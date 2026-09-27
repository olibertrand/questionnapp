import json
import re
import secrets
from concurrent.futures import ThreadPoolExecutor

from .. import db, engine_client, security
from ..web import HttpError, Response, int_list, json_response, require_str, router, to_int

MAX_TEMPLATE_SIZE = 200_000


def validate_template(template):
    if not isinstance(template, dict):
        raise HttpError(400, "Modèle invalide")
    if len(json.dumps(template)) > MAX_TEMPLATE_SIZE:
        raise HttpError(400, "Modèle trop volumineux")
    # génère une instance pour détecter les erreurs avant d'enregistrer
    engine_client.call_or_raise({"action": "generate", "template": template, "seed": secrets.randbits(32)})


def _chapter_id(conn, data):
    if data.get("chapter_name"):
        name = data["chapter_name"].strip()
        row = db.one(conn, "SELECT id FROM chapters WHERE name = ?", name)
        if row:
            return row["id"]
        pos = db.one(conn, "SELECT coalesce(max(position), 0) + 1 AS p FROM chapters")["p"]
        return db.insert(conn, "INSERT INTO chapters(name, position) VALUES (?, ?)", name, pos)
    cid = data.get("chapter_id")
    if cid in (None, ""):
        return None
    cid = to_int(cid, "chapitre")
    if not db.one(conn, "SELECT id FROM chapters WHERE id = ?", cid):
        raise HttpError(400, "Chapitre introuvable")
    return cid


def _set_skills(conn, qid, names, chapter_id):
    conn.execute("DELETE FROM question_skills WHERE question_id = ?", (qid,))
    for name in {n.strip() for n in names if isinstance(n, str) and n.strip()}:
        row = db.one(conn, "SELECT id FROM skills WHERE name = ?", name[:150])
        sid = row["id"] if row else db.insert(conn, "INSERT INTO skills(name, chapter_id) VALUES (?, ?)",
                                              name[:150], chapter_id)
        conn.execute("INSERT OR IGNORE INTO question_skills(question_id, skill_id) VALUES (?, ?)", (qid, sid))


def _set_classes(conn, user, qid, class_ids):
    """Met à jour les classes de la question, seulement parmi celles que l'utilisateur gère."""
    manageable = security.teacher_class_ids(conn, user)
    wanted = set(class_ids) & manageable
    for cid in manageable:
        if cid in wanted:
            conn.execute("INSERT OR IGNORE INTO class_questions(class_id, question_id) VALUES (?, ?)", (cid, qid))
        else:
            conn.execute("DELETE FROM class_questions WHERE class_id = ? AND question_id = ?", (cid, qid))


def _new_version(conn, qid, template):
    vid = db.insert(conn, "INSERT INTO question_versions(question_id, template, created_at) VALUES (?, ?, ?)",
                    qid, json.dumps(template, ensure_ascii=False), db.now())
    conn.execute("UPDATE questions SET version_id = ?, updated_at = ? WHERE id = ?", (vid, db.now(), qid))
    return vid


def save_question(conn, user, data, qid=None, validate=True):
    title = require_str(data, "title", 200)
    template = data.get("template")
    difficulty = to_int(data.get("difficulty", 2), "difficulté")
    if difficulty not in (1, 2, 3):
        raise HttpError(400, "Difficulté entre 1 et 3")
    if validate:
        validate_template(template)
    with db.Tx(conn):
        chapter_id = _chapter_id(conn, data)
        now = db.now()
        if qid is None:
            qid = db.insert(conn, """INSERT INTO questions(title, chapter_id, difficulty, author_id, created_at, updated_at)
                                     VALUES (?, ?, ?, ?, ?, ?)""", title, chapter_id, difficulty, user["id"], now, now)
            _new_version(conn, qid, template)
        else:
            current = db.one(conn, """SELECT v.template FROM questions q JOIN question_versions v ON v.id = q.version_id
                                      WHERE q.id = ?""", qid)
            conn.execute("UPDATE questions SET title = ?, chapter_id = ?, difficulty = ?, updated_at = ? WHERE id = ?",
                         (title, chapter_id, difficulty, now, qid))
            if not current or json.loads(current["template"]) != template:
                _new_version(conn, qid, template)
        if "skills" in data:
            _set_skills(conn, qid, data.get("skills") or [], chapter_id)
        if "class_ids" in data:
            _set_classes(conn, user, qid, int_list(data, "class_ids"))
    return qid


def question_row(conn, qid):
    q = db.one(conn, """
        SELECT q.id, q.title, q.chapter_id, c.name AS chapter, q.difficulty, q.archived, q.created_at,
               q.updated_at, q.version_id, v.template, coalesce(nullif(u.display_name, ''), u.username) AS author
        FROM questions q LEFT JOIN chapters c ON c.id = q.chapter_id
        LEFT JOIN question_versions v ON v.id = q.version_id
        LEFT JOIN users u ON u.id = q.author_id WHERE q.id = ?""", qid)
    if not q:
        raise HttpError(404, "Question introuvable")
    q["template"] = json.loads(q["template"])
    q["skills"] = [r["name"] for r in db.all_(conn, """
        SELECT s.name FROM question_skills qs JOIN skills s ON s.id = qs.skill_id
        WHERE qs.question_id = ? ORDER BY s.name""", qid)]
    q["class_ids"] = [r["class_id"] for r in db.all_(conn, "SELECT class_id FROM class_questions WHERE question_id = ?", qid)]
    return q


@router.get("/api/questions")
def list_questions(req):
    security.require_staff(req)
    where, args = ["1 = 1"], []
    if req.arg("archived") != "1":
        where.append("q.archived = 0")
    if req.arg("chapter_id"):
        where.append("q.chapter_id = ?")
        args.append(req.int_arg("chapter_id"))
    if req.arg("class_id"):
        where.append("q.id IN (SELECT question_id FROM class_questions WHERE class_id = ?)")
        args.append(req.int_arg("class_id"))
    if req.arg("q"):
        where.append("(q.title LIKE ? OR q.id IN (SELECT qs.question_id FROM question_skills qs "
                     "JOIN skills s ON s.id = qs.skill_id WHERE s.name LIKE ?))")
        args += [f"%{req.arg('q')}%"] * 2
    rows = db.all_(req.db, f"""
        SELECT q.id, q.title, q.chapter_id, c.name AS chapter, q.difficulty, q.archived, q.updated_at,
               (SELECT group_concat(s.name, ' | ') FROM question_skills qs JOIN skills s ON s.id = qs.skill_id
                WHERE qs.question_id = q.id) AS skills,
               (SELECT group_concat(cq.class_id) FROM class_questions cq WHERE cq.question_id = q.id) AS class_ids,
               (SELECT count(*) FROM attempts a WHERE a.question_id = q.id AND a.score IS NOT NULL) AS attempts,
               (SELECT avg(a.score) FROM attempts a WHERE a.question_id = q.id AND a.score IS NOT NULL) AS avg_score
        FROM questions q LEFT JOIN chapters c ON c.id = q.chapter_id
        WHERE {' AND '.join(where)} ORDER BY c.position, c.name, q.title""", *args)
    for r in rows:
        r["skills"] = r["skills"].split(" | ") if r["skills"] else []
        r["class_ids"] = [int(x) for x in r["class_ids"].split(",")] if r["class_ids"] else []
    return json_response({"questions": rows})


@router.get("/api/questions/export")
def export(req):
    security.require_staff(req)
    ids = [int(x) for x in (req.arg("ids") or "").split(",") if x.strip().isdigit()]
    if not ids:
        ids = [r["id"] for r in db.all_(req.db, "SELECT id FROM questions WHERE archived = 0")]
    out = []
    for qid in ids:
        q = question_row(req.db, qid)
        out.append({"title": q["title"], "chapter": q["chapter"], "difficulty": q["difficulty"],
                    "skills": q["skills"], "template": q["template"]})
    return json_response({"format": "questionnapp/questions", "version": 1, "questions": out})


def _selftest_messages(report):
    """Messages lisibles et sans doublon (« fields[0] » devient « réponse 1 »)."""
    def human(text):
        return re.sub(r"fields\[(\d+)\]", lambda m: f"réponse {int(m.group(1)) + 1}", text)
    msgs = []
    for e in report["errors"]:
        where = f" ({e['where']}{', ligne ' + str(e['line']) if e.get('line') else ''})" if e.get("where") else ""
        msgs.append(human(f"{e['error']}{where}"))
    msgs += [human(w) for w in report["warnings"]]
    return list(dict.fromkeys(msgs))


def selftest(template):
    return engine_client.call_or_raise({"action": "selftest", "template": template, "samples": 20}, timeout=75)


def selftest_many(templates, workers=4):
    """Auto-tests en parallèle : {id(template): rapport} (les modèles invalides sont ignorés)."""
    templates = [t for t in templates if isinstance(t, dict)]

    def one(t):
        try:
            return id(t), selftest(t)
        except HttpError:
            return id(t), None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return {k: v for k, v in pool.map(one, templates) if v is not None}


def _import_items(conn, user, items, class_ids, validate=True, skip_existing=False):
    """Importe une liste de questions. Avec `validate`, chaque modèle passe l'auto-test du moteur :
    une question qui ne se génère pas est refusée ; une question importée mais suspecte
    (correction refusée, tests laxistes, peu de variété) est signalée dans `warnings`."""
    existing = {r["title"] for r in db.all_(conn, "SELECT title FROM questions WHERE archived = 0")} if skip_existing else set()
    created, skipped, errors, warnings = [], [], [], []
    reports = selftest_many([it.get("template") for it in items if isinstance(it, dict) and it.get("title") not in existing]) \
        if validate else {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"question {i + 1} : format invalide")
            continue
        title = item.get("title") or "?"
        if title in existing:
            skipped.append(title)
            continue
        try:
            template = item.get("template")
            if validate:
                if not isinstance(template, dict):
                    raise HttpError(400, "modèle manquant")
                report = reports.get(id(template)) or selftest(template)
                generation_failed = [e for e in report["errors"] if "référence" not in e["error"]]
                if generation_failed or not report["samples"]:
                    raise HttpError(422, "; ".join(_selftest_messages(report)[:3]) or "génération impossible")
            payload = {"title": item.get("title"), "difficulty": item.get("difficulty", 2),
                       "skills": item.get("skills") or [], "template": template,
                       "chapter_name": item.get("chapter") or None, "class_ids": class_ids}
            qid = save_question(conn, user, payload, validate=False)
            created.append(qid)
            if validate and report["status"] != "ok":
                warnings.append({"id": qid, "title": title, "messages": _selftest_messages(report)})
        except HttpError as exc:
            errors.append(f"question {i + 1} ({title}) : {exc.message}")
    return {"created": created, "skipped": skipped, "errors": errors, "warnings": warnings}


@router.post("/api/questions/import")
def import_questions(req):
    user = security.require_staff(req)
    data = req.json
    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise HttpError(400, "Liste « questions » attendue")
    class_ids = int_list(data, "class_ids") if isinstance(data, dict) and "class_ids" in data else []
    validate = data.get("validate", True) if isinstance(data, dict) else True
    return json_response(_import_items(req.db, user, items, class_ids, validate))


@router.get("/api/questions/referential")
def referential(req):
    """Chapitres, compétences et questions existantes au format Markdown, à fournir à une IA
    (projet Claude) pour qu'elle réutilise les mêmes noms et évite les doublons."""
    security.require_staff(req)
    conn = req.db
    chapters = db.all_(conn, "SELECT id, name FROM chapters ORDER BY position, name")
    lines = ["# Référentiel QuestionnApp", "",
             "Chapitres, compétences et questions déjà présentes dans la banque. Réutiliser exactement ces noms "
             "de chapitres et de compétences quand ils conviennent ; n'en créer de nouveaux que si nécessaire.", ""]
    for ch in chapters + [{"id": None, "name": "Sans chapitre"}]:
        qs = db.all_(conn, """SELECT q.id, q.title, q.difficulty,
                                     (SELECT group_concat(s.name, ' ; ') FROM question_skills qs JOIN skills s ON s.id = qs.skill_id
                                      WHERE qs.question_id = q.id) AS skills
                              FROM questions q WHERE q.archived = 0 AND q.chapter_id IS ? ORDER BY q.title""", ch["id"])
        skills = db.all_(conn, """SELECT DISTINCT s.name FROM skills s LEFT JOIN question_skills qs ON qs.skill_id = s.id
                                  LEFT JOIN questions q ON q.id = qs.question_id
                                  WHERE s.chapter_id IS ? OR q.chapter_id IS ? ORDER BY s.name""", ch["id"], ch["id"])
        if ch["id"] is None and not qs:
            continue
        lines.append(f"## Chapitre : {ch['name']}")
        lines.append("Compétences : " + (" ; ".join(s["name"] for s in skills) if skills else "(aucune)"))
        lines.append("")
        for q in qs:
            lines.append(f"- {q['title']} (difficulté {q['difficulty']}) — {q['skills'] or 'sans compétence'}")
        lines.append("")
    return Response("\n".join(lines), content_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="referentiel-questionnapp.md"'})


@router.post("/api/questions/preview")
def preview(req):
    security.require_staff(req)
    data = req.json
    seed = data.get("seed")
    seed = secrets.randbits(32) if seed in (None, "") else to_int(seed, "graine")
    res = engine_client.call({"action": "preview", "template": data.get("template"), "seed": seed})
    return json_response(res)


@router.post("/api/questions/selftest")
def selftest_route(req):
    security.require_staff(req)
    template = req.json.get("template")
    if not isinstance(template, dict):
        raise HttpError(400, "Modèle invalide")
    report = selftest(template)
    report["messages"] = _selftest_messages(report)
    return json_response(report)


@router.post("/api/questions/try")
def try_answer(req):
    security.require_staff(req)
    data = req.json
    res = engine_client.call({"action": "check", "template": data.get("template"),
                              "seed": to_int(data.get("seed"), "graine"), "answers": data.get("answers") or []})
    return json_response(res)


@router.post("/api/questions")
def create(req):
    user = security.require_staff(req)
    qid = save_question(req.db, user, req.json)
    return json_response({"id": qid}, 201)


@router.get("/api/questions/:id")
def get(req):
    security.require_staff(req)
    return json_response({"question": question_row(req.db, to_int(req.params["id"]))})


@router.put("/api/questions/:id")
def update(req):
    user = security.require_staff(req)
    qid = to_int(req.params["id"])
    question_row(req.db, qid)
    save_question(req.db, user, req.json, qid)
    if "archived" in req.json:
        req.db.execute("UPDATE questions SET archived = ? WHERE id = ?", (1 if req.json["archived"] else 0, qid))
    return json_response({"id": qid})


@router.post("/api/questions/:id/duplicate")
def duplicate(req):
    user = security.require_staff(req)
    q = question_row(req.db, to_int(req.params["id"]))
    qid = save_question(req.db, user, {"title": q["title"] + " (copie)", "chapter_id": q["chapter_id"],
                                       "difficulty": q["difficulty"], "skills": q["skills"],
                                       "template": q["template"]}, validate=False)
    return json_response({"id": qid}, 201)


@router.delete("/api/questions/:id")
def delete(req):
    security.require_staff(req)
    qid = to_int(req.params["id"])
    question_row(req.db, qid)
    if db.one(req.db, "SELECT 1 FROM attempts WHERE question_id = ? LIMIT 1", qid):
        req.db.execute("UPDATE questions SET archived = 1 WHERE id = ?", (qid,))
        return json_response({"archived": True})
    req.db.execute("DELETE FROM questions WHERE id = ?", (qid,))
    return json_response({"deleted": True})


@router.post("/api/questions/bulk-classes")
def bulk_classes(req):
    """Ajoute ou retire un lot de questions d'un lot de classes."""
    user = security.require_staff(req)
    data = req.json
    qids, cids = int_list(data, "question_ids"), int_list(data, "class_ids")
    add = bool(data.get("add", True))
    with db.Tx(req.db):
        for cid in cids:
            security.require_class_access(req.db, user, cid)
            for qid in qids:
                if add:
                    req.db.execute("INSERT OR IGNORE INTO class_questions(class_id, question_id) VALUES (?, ?)",
                                   (cid, qid))
                else:
                    req.db.execute("DELETE FROM class_questions WHERE class_id = ? AND question_id = ?", (cid, qid))
    return json_response({"ok": True})


