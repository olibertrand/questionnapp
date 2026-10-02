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


UID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def clean_uid(uid):
    if uid in (None, ""):
        return None
    if not isinstance(uid, str) or not UID_RE.match(uid.strip()):
        raise HttpError(400, f"Identifiant de question invalide : {uid!r} (lettres, chiffres, - et _)")
    return uid.strip().upper()


def find_existing(conn, item):
    """Question déjà présente pour un élément importé : même identifiant, sinon même titre
    (parmi les questions non archivées). Renvoie {id, archived, template} ou None."""
    uid = clean_uid(item.get("uid"))
    row = None
    if uid:
        row = db.one(conn, """SELECT q.id, q.archived, v.template FROM questions q
                              LEFT JOIN question_versions v ON v.id = q.version_id WHERE q.uid = ?""", uid)
    if not row and item.get("title"):
        row = db.one(conn, """SELECT q.id, q.archived, v.template FROM questions q
                              LEFT JOIN question_versions v ON v.id = q.version_id
                              WHERE q.title = ? AND q.archived = 0 ORDER BY q.id LIMIT 1""", item["title"])
    if row:
        row["template"] = json.loads(row["template"]) if row["template"] else None
    return row


def save_question(conn, user, data, qid=None, validate=True):
    title = require_str(data, "title", 200)
    uid = clean_uid(data.get("uid"))
    template = data.get("template")
    difficulty = to_int(data.get("difficulty", 2), "difficulté")
    if difficulty not in (1, 2, 3):
        raise HttpError(400, "Difficulté entre 1 et 3")
    if validate:
        validate_template(template)
    with db.Tx(conn):
        chapter_id = _chapter_id(conn, data)
        now = db.now()
        if uid and db.one(conn, "SELECT 1 FROM questions WHERE uid = ? AND id IS NOT ?", uid, qid):
            raise HttpError(409, f"L'identifiant {uid} est déjà utilisé par une autre question")
        if qid is None:
            qid = db.insert(conn, """INSERT INTO questions(uid, title, chapter_id, difficulty, author_id, created_at, updated_at)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""", uid, title, chapter_id, difficulty, user["id"], now, now)
            if not uid:
                conn.execute("UPDATE questions SET uid = ? WHERE id = ?", (f"Q-{qid:04d}", qid))
            _new_version(conn, qid, template)
        else:
            current = db.one(conn, """SELECT v.template FROM questions q JOIN question_versions v ON v.id = q.version_id
                                      WHERE q.id = ?""", qid)
            conn.execute("UPDATE questions SET title = ?, chapter_id = ?, difficulty = ?, updated_at = ? WHERE id = ?",
                         (title, chapter_id, difficulty, now, qid))
            if uid:
                conn.execute("UPDATE questions SET uid = ? WHERE id = ?", (uid, qid))
            if not current or json.loads(current["template"]) != template:
                _new_version(conn, qid, template)
        if "skills" in data:
            _set_skills(conn, qid, data.get("skills") or [], chapter_id)
        if "class_ids" in data:
            _set_classes(conn, user, qid, int_list(data, "class_ids"))
    return qid


def question_row(conn, qid):
    q = db.one(conn, """
        SELECT q.id, q.uid, q.title, q.chapter_id, c.name AS chapter, q.difficulty, q.archived, q.created_at,
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
        where.append("(q.title LIKE ? OR q.uid LIKE ? OR q.id IN (SELECT qs.question_id FROM question_skills qs "
                     "JOIN skills s ON s.id = qs.skill_id WHERE s.name LIKE ?))")
        args += [f"%{req.arg('q')}%"] * 3
    rows = db.all_(req.db, f"""
        SELECT q.id, q.uid, q.title, q.chapter_id, c.name AS chapter, q.difficulty, q.archived, q.updated_at,
               (SELECT v.sample FROM question_versions v WHERE v.id = q.version_id) AS sample,
               (SELECT group_concat(s.name, ' | ') FROM question_skills qs JOIN skills s ON s.id = qs.skill_id
                WHERE qs.question_id = q.id) AS skills,
               (SELECT group_concat(cq.class_id) FROM class_questions cq WHERE cq.question_id = q.id) AS class_ids,
               (SELECT count(*) FROM attempts a WHERE a.question_id = q.id AND a.score IS NOT NULL) AS attempts,
               (SELECT avg(a.score) FROM attempts a WHERE a.question_id = q.id AND a.score IS NOT NULL) AS avg_score
        FROM questions q LEFT JOIN chapters c ON c.id = q.chapter_id
        WHERE {' AND '.join(where)} ORDER BY c.position, c.name, q.uid, q.title""", *args)
    for r in rows:
        r["skills"] = r["skills"].split(" | ") if r["skills"] else []
        r["class_ids"] = [int(x) for x in r["class_ids"].split(",")] if r["class_ids"] else []
        r["sample"] = json.loads(r["sample"]) if r["sample"] else None
    return json_response({"questions": rows})


def _sample_of(public):
    """Ce qu'on montre d'une question dans la liste : l'énoncé et l'intitulé des champs (pas les options d'un QCM)."""
    return {"statement": public["statement"],
            "fields": [{"type": f["type"], "label": f.get("label", "")} for f in public["fields"]]}


@router.post("/api/questions/samples")
def samples(req):
    """Un exemple d'énoncé par question (généré au besoin, puis mémorisé pour la version courante)."""
    security.require_staff(req)
    ids = int_list(req.json, "ids")[:60]
    if not ids:
        return json_response({"samples": {}})
    marks = ",".join("?" * len(ids))
    rows = db.all_(req.db, f"""SELECT q.id, q.version_id, v.template, v.sample FROM questions q
                               JOIN question_versions v ON v.id = q.version_id WHERE q.id IN ({marks})""", *ids)
    out = {r["id"]: json.loads(r["sample"]) for r in rows if r["sample"]}
    todo = [r for r in rows if not r["sample"]]

    def one(r):
        res = engine_client.call({"action": "generate", "template": json.loads(r["template"]), "seed": secrets.randbits(32)})
        if res.get("ok"):
            return r, _sample_of(res["result"]["public"])
        return r, {"error": res.get("error", "génération impossible")}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, todo))
    for r, sample in results:
        out[r["id"]] = sample
        if "error" not in sample:
            req.db.execute("UPDATE question_versions SET sample = ? WHERE id = ?",
                           (json.dumps(sample, ensure_ascii=False), r["version_id"]))
    return json_response({"samples": {str(k): v for k, v in out.items()}})


@router.get("/api/questions/export")
def export(req):
    security.require_staff(req)
    ids = [int(x) for x in (req.arg("ids") or "").split(",") if x.strip().isdigit()]
    if not ids:
        ids = [r["id"] for r in db.all_(req.db, "SELECT id FROM questions WHERE archived = 0")]
    out = []
    for qid in ids:
        q = question_row(req.db, qid)
        out.append({"uid": q["uid"], "title": q["title"], "chapter": q["chapter"], "difficulty": q["difficulty"],
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


def _import_items(conn, user, items, class_ids, validate=True):
    """Importe une liste de questions. Une question déjà présente (même identifiant, sinon même
    titre) n'est jamais réimportée : elle est comptée dans `skipped` (ou restaurée si elle avait
    été archivée). Avec `validate`, chaque modèle passe l'auto-test du moteur : une question qui
    ne se génère pas est refusée ; une question importée mais suspecte est signalée dans `warnings`."""
    created, skipped, restored, errors, warnings = [], [], [], [], []
    fresh = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("title"):
            errors.append(f"question {i + 1} : format invalide (titre manquant)")
            continue
        try:
            existing = find_existing(conn, item)
        except HttpError as exc:
            errors.append(f"question {i + 1} ({item.get('title')}) : {exc.message}")
            continue
        if existing:
            if existing["archived"]:
                conn.execute("UPDATE questions SET archived = 0 WHERE id = ?", (existing["id"],))
                restored.append(item["title"])
            else:
                skipped.append(item["title"])
            continue
        fresh.append(item)
    reports = selftest_many([it.get("template") for it in fresh]) if validate else {}
    seen = set()
    for item in fresh:
        title = item["title"]
        key = clean_uid(item.get("uid")) or title
        if key in seen:  # doublon à l'intérieur du fichier lui-même
            skipped.append(title)
            continue
        seen.add(key)
        try:
            template = item.get("template")
            if validate:
                if not isinstance(template, dict):
                    raise HttpError(400, "modèle manquant")
                report = reports.get(id(template)) or selftest(template)
                generation_failed = [e for e in report["errors"] if "référence" not in e["error"]]
                if generation_failed or not report["samples"]:
                    raise HttpError(422, "; ".join(_selftest_messages(report)[:3]) or "génération impossible")
            payload = {"uid": item.get("uid"), "title": title, "difficulty": item.get("difficulty", 2),
                       "skills": item.get("skills") or [], "template": template,
                       "chapter_name": item.get("chapter") or None, "class_ids": class_ids}
            qid = save_question(conn, user, payload, validate=False)
            created.append(qid)
            if validate and report["status"] != "ok":
                warnings.append({"id": qid, "title": title, "messages": _selftest_messages(report)})
        except HttpError as exc:
            errors.append(f"« {title} » : {exc.message}")
    return {"created": created, "skipped": skipped, "restored": restored, "errors": errors, "warnings": warnings}


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
    r = delete_questions(req.db, [qid])
    return json_response({"archived": bool(r["archived"]), "deleted": bool(r["deleted"])})


def delete_questions(conn, ids, purge=False):
    """Supprime les questions ; celles auxquelles des élèves ont répondu sont archivées
    (statistiques conservées), sauf avec `purge` qui efface aussi les réponses."""
    deleted, archived = 0, 0
    with db.Tx(conn):
        for qid in ids:
            if not db.one(conn, "SELECT id FROM questions WHERE id = ?", qid):
                continue
            if not purge and db.one(conn, "SELECT 1 FROM attempts WHERE question_id = ? LIMIT 1", qid):
                conn.execute("UPDATE questions SET archived = 1 WHERE id = ?", (qid,))
                conn.execute("DELETE FROM class_questions WHERE question_id = ?", (qid,))
                archived += 1
            else:
                conn.execute("DELETE FROM attempts WHERE question_id = ?", (qid,))
                conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
                deleted += 1
    return {"deleted": deleted, "archived": archived}


@router.post("/api/questions/bulk-delete")
def bulk_delete(req):
    user = security.require_staff(req)
    data = req.json
    purge = bool(data.get("purge"))
    if purge and not security.is_admin(user):
        raise HttpError(403, "Seul un administrateur peut effacer les réponses des élèves")
    return json_response(delete_questions(req.db, int_list(data, "ids"), purge))


def _duplicate_groups(conn):
    """Questions actives de même titre : [(à garder, [doublons])]. On garde celle qui a le plus de
    réponses d'élèves, puis celle qui a un identifiant de banque, puis la plus ancienne."""
    rows = db.all_(conn, """SELECT q.id, q.uid, q.title,
                                   (SELECT count(*) FROM attempts a WHERE a.question_id = q.id) AS n
                            FROM questions q WHERE q.archived = 0 ORDER BY q.title, q.id""")
    groups = {}
    for r in rows:
        groups.setdefault(r["title"], []).append(r)
    out = []
    for title, qs in groups.items():
        if len(qs) < 2:
            continue
        qs.sort(key=lambda r: (-r["n"], (r["uid"] or "Q-").startswith("Q-"), r["id"]))
        out.append((qs[0], qs[1:]))
    return out


@router.get("/api/questions/duplicates")
def list_duplicates(req):
    security.require_staff(req)
    return json_response({"groups": [{"keep": k, "remove": r} for k, r in _duplicate_groups(req.db)]})


@router.post("/api/questions/remove-duplicates")
def remove_duplicates(req):
    """Supprime les doublons (même titre) en gardant une question par titre ; les affectations
    aux classes et aux séances des doublons sont reportées sur la question gardée."""
    security.require_staff(req)
    conn = req.db
    groups = _duplicate_groups(conn)
    with db.Tx(conn):
        for keep, dups in groups:
            for d in dups:
                conn.execute("""INSERT OR IGNORE INTO class_questions(class_id, question_id)
                                SELECT class_id, ? FROM class_questions WHERE question_id = ?""", (keep["id"], d["id"]))
                conn.execute("""INSERT OR IGNORE INTO assignment_questions(assignment_id, question_id, position)
                                SELECT assignment_id, ?, position FROM assignment_questions WHERE question_id = ?""",
                             (keep["id"], d["id"]))
                conn.execute("DELETE FROM assignment_questions WHERE question_id = ?", (d["id"],))
    result = delete_questions(conn, [d["id"] for _, dups in groups for d in dups])
    result["groups"] = len(groups)
    return json_response(result)


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


