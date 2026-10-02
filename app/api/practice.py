"""Travail de l'élève : séances du jour, entraînement par chapitre, mode adaptatif."""

import datetime
import json
import secrets
from collections import defaultdict

from .. import adaptive, db, engine_client, security
from ..web import HttpError, json_response, router, to_int
from .assignments import VISIBLE_SQL, assignment_questions, is_visible, progress


def _student_class_ids(conn, user_id):
    return [r["class_id"] for r in db.all_(conn, "SELECT class_id FROM class_members WHERE user_id = ?", user_id)]


def _question_available(conn, user, qid):
    if user["role"] in ("admin", "teacher"):
        return bool(db.one(conn, "SELECT 1 FROM questions WHERE id = ? AND version_id IS NOT NULL", qid))
    return any(q["id"] == qid for q in adaptive.available_questions(conn, user["id"]))


def _avoid_list(conn, user_id, qid):
    """Empreintes déjà vues par l'élève + celles servies à d'autres dans les 3 dernières heures
    (deux voisins n'ont pas les mêmes données)."""
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).isoformat()[:19] + "Z"
    rows = db.all_(conn, """SELECT DISTINCT fingerprint FROM attempts WHERE question_id = ?
                            AND (user_id = ? OR created_at >= ?) ORDER BY id DESC LIMIT 400""", qid, user_id, since)
    return [r["fingerprint"] for r in rows]


def create_attempt(conn, user, qid, mode, assignment_id=None):
    q = db.one(conn, """SELECT q.id, q.uid, q.title, q.version_id, v.template, c.name AS chapter FROM questions q
                        JOIN question_versions v ON v.id = q.version_id LEFT JOIN chapters c ON c.id = q.chapter_id
                        WHERE q.id = ?""", qid)
    if not q:
        raise HttpError(404, "Question introuvable")
    inst = engine_client.call_or_raise({
        "action": "generate", "template": json.loads(q["template"]), "seed": secrets.randbits(32),
        "avoid": _avoid_list(conn, user["id"], qid)}, status=500)
    aid = db.insert(conn, """INSERT INTO attempts(user_id, question_id, version_id, assignment_id, mode, seed,
                                                 fingerprint, instance, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    user["id"], qid, q["version_id"], assignment_id, mode, inst["seed"], inst["fingerprint"],
                    json.dumps(inst["public"], ensure_ascii=False), db.now())
    return {"id": aid, "mode": mode, "assignment_id": assignment_id,
            "question": {"id": qid, "uid": q["uid"], "title": q["title"], "chapter": q["chapter"]}, "instance": inst["public"]}


def _load_assignment_for_student(conn, user, aid):
    a = db.one(conn, "SELECT * FROM assignments WHERE id = ?", aid)
    if not a:
        raise HttpError(404, "Séance introuvable")
    if user["role"] == "student":
        if not is_visible(conn, aid, user["id"]):
            if a["class_id"] in _student_class_ids(conn, user["id"]) and not a["active"]:
                raise HttpError(403, "Cette séance a été désactivée par votre professeur")
            raise HttpError(403, "Cette séance ne vous est pas destinée")
    elif not security.is_admin(user):
        security.require_class_access(conn, user, a["class_id"])
    return a


@router.post("/api/practice/next")
def next_question(req):
    user = security.require_user(req)
    data = req.json
    mode = data.get("mode")
    conn = req.db
    if mode == "assignment":
        a = _load_assignment_for_student(conn, user, to_int(data.get("assignment_id"), "séance"))
        prog = progress(conn, a["id"], user["id"])
        qids = [r["question_id"] for r in prog["questions"]]
        if data.get("question_id") is not None:
            qid = to_int(data["question_id"])
            if qid not in qids:
                raise HttpError(400, "Question hors de la séance")
        else:
            todo = [r["question_id"] for r in prog["questions"] if (r["best"] or 0) < 1]
            if not todo:
                return json_response({"done": True, "progress": prog})
            last = db.one(conn, "SELECT question_id FROM attempts WHERE user_id = ? AND assignment_id = ? "
                                "AND score IS NOT NULL ORDER BY answered_at DESC LIMIT 1", user["id"], a["id"])
            qid = next((q for q in todo if not last or q != last["question_id"]), todo[0])
        attempt = create_attempt(conn, user, qid, "assignment", a["id"])
        attempt["context"] = {"assignment": {"id": a["id"], "title": a["title"], "day": a["day"]}, "progress": prog}
        return json_response({"attempt": attempt})
    if mode in ("chapter", "adaptive"):
        chapter_id = data.get("chapter_id")
        chapter_id = to_int(chapter_id, "chapitre") if chapter_id not in (None, "") else None
        if mode == "chapter" and chapter_id is None:
            raise HttpError(400, "Chapitre requis")
        q = (adaptive.pick_chapter(conn, user["id"], chapter_id) if mode == "chapter"
             else adaptive.pick_adaptive(conn, user["id"], chapter_id))
        if not q:
            raise HttpError(404, "Aucune question disponible pour l'instant")
        attempt = create_attempt(conn, user, q["id"], mode)
        if chapter_id is not None:
            ch = db.one(conn, "SELECT id, name FROM chapters WHERE id = ?", chapter_id)
            attempt["context"] = {"chapter": ch}
        return json_response({"attempt": attempt})
    if mode == "free":
        qid = to_int(data.get("question_id"))
        if not _question_available(conn, user, qid):
            raise HttpError(403, "Question non disponible")
        return json_response({"attempt": create_attempt(conn, user, qid, "free")})
    raise HttpError(400, "Mode inconnu")


def _load_attempt(req, for_answer=False):
    user = security.require_user(req)
    aid = to_int(req.params["id"])
    a = db.one(req.db, """SELECT a.*, q.uid, q.title, c.name AS chapter, v.template FROM attempts a
                          JOIN questions q ON q.id = a.question_id LEFT JOIN chapters c ON c.id = q.chapter_id
                          JOIN question_versions v ON v.id = a.version_id WHERE a.id = ?""", aid)
    if not a:
        raise HttpError(404, "Tentative introuvable")
    if for_answer or a["user_id"] != user["id"]:
        if a["user_id"] != user["id"]:
            if for_answer or user["role"] == "student":
                raise HttpError(403, "Accès refusé")
            security.require_student_visibility(req.db, user, a["user_id"])
    return user, a


def try_factor(tries):
    """Coefficient appliqué au score selon l'essai : 100 %, 75 %, 50 %, puis 25 %."""
    return max(0.25, 1 - 0.25 * (max(tries, 1) - 1))


def _is_blank(value):
    return value is None or value == [] or (isinstance(value, str) and not value.strip())


def _public_feedback(result):
    """Retour d'un essai intermédiaire : juste / faux et commentaires, sans la solution."""
    return {"score": result["score"], "correct": result["correct"],
            "fields": [{"score": f["score"], "correct": f["correct"], "feedback": f["feedback"]} for f in result["fields"]]}


def _finalize(req, a, answers, result, raw_score, tries, history, gave_up=False):
    score = round(raw_score * try_factor(tries), 3)
    # score = score retenu (pondéré par l'essai) ; raw_score = réussite du dernier essai
    result = dict(result, score=score, raw_score=raw_score, tries=tries, gave_up=gave_up)
    cur = req.db.execute("UPDATE attempts SET answers = ?, result = ?, score = ?, tries = ?, history = ?, answered_at = ? "
                         "WHERE id = ? AND score IS NULL",
                         (json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False), score,
                          tries, json.dumps(history, ensure_ascii=False), db.now(), a["id"]))
    if cur.rowcount == 0:
        raise HttpError(409, "Question déjà corrigée")
    return result


@router.post("/api/attempts/:id/answer")
def answer(req):
    """Un essai. Tant qu'il reste des essais et que tout n'est pas juste, on renvoie seulement
    ce qui est juste ou faux, les commentaires (tests de code, indices SQL) et un indice ;
    la solution n'est donnée qu'à la fin."""
    user, a = _load_attempt(req, for_answer=True)
    if a["score"] is not None:
        raise HttpError(409, "Question déjà corrigée : demandez-en une nouvelle")
    answers = req.json.get("answers") if isinstance(req.json, dict) else None
    if not isinstance(answers, list) or len(json.dumps(answers)) > 100_000:
        raise HttpError(400, "Réponses invalides")
    instance = json.loads(a["instance"])
    if len(answers) < len(instance["fields"]) or any(_is_blank(x) for x in answers[:len(instance["fields"])]):
        raise HttpError(400, "Répondez à toutes les questions avant de valider (un essai n'est pas décompté).")
    result = engine_client.call_or_raise({"action": "check", "template": json.loads(a["template"]),
                                          "seed": a["seed"], "answers": answers}, status=500)
    tries = (a["tries"] or 0) + 1
    history = (json.loads(a["history"]) if a["history"] else []) + [
        {"answers": answers, "score": result["score"], "at": db.now()}]
    limit = instance.get("max_tries") or result.get("max_tries") or 1
    out = {"tries": tries, "max_tries": limit}
    if result["correct"] or tries >= limit:
        out["final"] = True
        out["result"] = _finalize(req, a, answers, result, result["score"], tries, history)
    else:
        cur = req.db.execute("UPDATE attempts SET tries = ?, history = ? WHERE id = ? AND score IS NULL AND tries = ?",
                             (tries, json.dumps(history, ensure_ascii=False), a["id"], a["tries"] or 0))
        if cur.rowcount == 0:
            raise HttpError(409, "Essai déjà enregistré, rechargez la page")
        out["final"] = False
        out["result"] = _public_feedback(result)
        out["hints"] = result["hints"][:tries]  # un indice de plus à chaque essai
    if a["assignment_id"] and out["final"]:
        out["progress"] = progress(req.db, a["assignment_id"], user["id"])
    return json_response(out)


@router.post("/api/attempts/:id/reveal")
def reveal(req):
    """L'élève renonce : on affiche la solution ; le score est celui du dernier essai (pondéré)."""
    user, a = _load_attempt(req, for_answer=True)
    if a["score"] is not None:
        raise HttpError(409, "Question déjà corrigée")
    history = json.loads(a["history"]) if a["history"] else []
    answers = req.json.get("answers") if isinstance(req.json, dict) else None
    if not isinstance(answers, list):
        answers = history[-1]["answers"] if history else []
    result = engine_client.call_or_raise({"action": "check", "template": json.loads(a["template"]),
                                          "seed": a["seed"], "answers": answers}, status=500)
    last = history[-1]["score"] if history else 0.0
    out = {"final": True, "tries": a["tries"] or 0,
           "result": _finalize(req, a, answers, result, last, a["tries"] or 1, history, gave_up=True)}
    if a["assignment_id"]:
        out["progress"] = progress(req.db, a["assignment_id"], user["id"])
    return json_response(out)


@router.get("/api/attempts/:id")
def get_attempt(req):
    _user, a = _load_attempt(req)
    return json_response({"attempt": {
        "id": a["id"], "user_id": a["user_id"], "question_id": a["question_id"], "uid": a["uid"], "title": a["title"],
        "chapter": a["chapter"], "mode": a["mode"], "assignment_id": a["assignment_id"],
        "created_at": a["created_at"], "answered_at": a["answered_at"], "score": a["score"], "tries": a["tries"],
        "history": json.loads(a["history"]) if a["history"] else [],
        "instance": json.loads(a["instance"]), "answers": json.loads(a["answers"]) if a["answers"] else None,
        "result": json.loads(a["result"]) if a["result"] else None}})


@router.get("/api/me/dashboard")
def dashboard(req):
    user = security.require_user(req)
    conn = req.db
    uid = user["id"]
    classes = db.all_(conn, """SELECT c.id, c.name FROM classes c JOIN class_members m ON m.class_id = c.id
                               WHERE m.user_id = ? ORDER BY c.name""", uid)
    since = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
    # séances actives qui le concernent : thématiques (sans date) et datées des 45 derniers jours ou à venir
    assigns = conn.execute(f"""SELECT a.id, a.title, a.day, a.kind, a.class_id, c.name AS class_name
                               FROM assignments a JOIN classes c ON c.id = a.class_id
                               WHERE {VISIBLE_SQL} AND (a.kind = 'theme' OR a.day >= :since)
                               ORDER BY a.day, a.id""", {"u": uid, "since": since}).fetchall()
    for a in assigns:
        p = progress(conn, a["id"], uid)
        a["progress"] = {k: p[k] for k in ("total", "done", "mastered", "score")}

    available = adaptive.available_questions(conn, uid)
    qids = [q["id"] for q in available]
    history = defaultdict(list)
    for r in db.all_(conn, "SELECT question_id, score FROM attempts WHERE user_id = ? AND score IS NOT NULL "
                           "ORDER BY answered_at DESC, id DESC", uid):
        history[r["question_id"]].append(r["score"])
    chapters = {}
    for q in available:
        ch = chapters.setdefault(q["chapter_id"], {"id": q["chapter_id"], "questions": 0, "scores": [], "seen": 0})
        ch["questions"] += 1
        ch["scores"] += history.get(q["id"], [])[:5]
        ch["seen"] += 1 if q["id"] in history else 0
    names = {r["id"]: r for r in db.all_(conn, "SELECT id, name, position FROM chapters")}
    chapter_list = []
    for cid, ch in chapters.items():
        info = names.get(cid, {"name": "Sans chapitre", "position": 9999})
        chapter_list.append({"id": cid, "name": info["name"], "position": info["position"],
                             "questions": ch["questions"], "seen": ch["seen"],
                             "mastery": round(adaptive.weighted_mastery(ch["scores"]), 3) if ch["scores"] else None})
    chapter_list.sort(key=lambda c: (c["position"], c["name"]))

    qskills = adaptive.question_skills(conn, qids)
    skill_ids = sorted({s for sk in qskills.values() for s in sk})
    mastery = adaptive.skill_mastery(conn, [uid]).get(uid, {})
    skill_names = {r["id"]: r["name"] for r in db.all_(conn, "SELECT id, name FROM skills")}
    skills = [{"id": s, "name": skill_names.get(s, "?"), **mastery.get(s, {"mastery": None, "attempts": 0})}
              for s in skill_ids]
    skills.sort(key=lambda s: (s["mastery"] is None, s["mastery"] if s["mastery"] is not None else 0))

    recent = db.all_(conn, """SELECT a.id, a.score, a.answered_at, a.mode, q.title FROM attempts a
                              JOIN questions q ON q.id = a.question_id
                              WHERE a.user_id = ? AND a.score IS NOT NULL ORDER BY a.answered_at DESC LIMIT 10""", uid)
    week = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()[:19] + "Z"
    totals = db.one(conn, """SELECT count(*) AS answered, avg(score) AS avg,
                             sum(CASE WHEN answered_at >= ? THEN 1 ELSE 0 END) AS week
                             FROM attempts WHERE user_id = ? AND score IS NOT NULL""", week, uid)
    return json_response({"today": db.today(), "classes": classes, "assignments": assigns,
                          "chapters": chapter_list, "skills": skills, "recent": recent, "totals": totals})


@router.get("/api/me/assignments/:id")
def my_assignment(req):
    user = security.require_user(req)
    a = _load_assignment_for_student(req.db, user, to_int(req.params["id"]))
    a["questions"] = assignment_questions(req.db, a["id"])
    a["progress"] = progress(req.db, a["id"], user["id"])
    return json_response({"assignment": a})


@router.get("/api/me/history")
def history(req):
    user = security.require_user(req)
    limit = min(req.int_arg("limit", 50), 500)
    rows = db.all_(req.db, """SELECT a.id, a.mode, a.score, a.created_at, a.answered_at, q.title, c.name AS chapter
                              FROM attempts a JOIN questions q ON q.id = a.question_id
                              LEFT JOIN chapters c ON c.id = q.chapter_id
                              WHERE a.user_id = ? AND a.score IS NOT NULL ORDER BY a.answered_at DESC LIMIT ?""",
                   user["id"], limit)
    return json_response({"attempts": rows})
