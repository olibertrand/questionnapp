"""Séances : questions données à une classe pour un jour donné."""

import datetime

from .. import db, security
from ..web import HttpError, int_list, json_response, require_str, router, to_int


def _check_day(day):
    try:
        return datetime.date.fromisoformat(day).isoformat()
    except (TypeError, ValueError):
        raise HttpError(400, "Date invalide (AAAA-MM-JJ)") from None


def _set_questions(conn, aid, class_id, qids):
    conn.execute("DELETE FROM assignment_questions WHERE assignment_id = ?", (aid,))
    for pos, qid in enumerate(qids):
        if not db.one(conn, "SELECT id FROM questions WHERE id = ?", qid):
            raise HttpError(400, f"Question {qid} introuvable")
        conn.execute("INSERT OR IGNORE INTO assignment_questions(assignment_id, question_id, position) VALUES (?, ?, ?)",
                     (aid, qid, pos))
        # une question donnée en séance est aussi affectée à la classe (entraînement)
        conn.execute("INSERT OR IGNORE INTO class_questions(class_id, question_id) VALUES (?, ?)", (class_id, qid))


def assignment_questions(conn, aid):
    return db.all_(conn, """SELECT q.id, q.title, c.name AS chapter FROM assignment_questions aq
                            JOIN questions q ON q.id = aq.question_id LEFT JOIN chapters c ON c.id = q.chapter_id
                            WHERE aq.assignment_id = ? ORDER BY aq.position""", aid)


def progress(conn, aid, user_id):
    """Meilleur score par question de la séance pour un élève."""
    rows = db.all_(conn, """SELECT aq.question_id, max(a.score) AS best, count(a.score) AS tries
                            FROM assignment_questions aq
                            LEFT JOIN attempts a ON a.question_id = aq.question_id AND a.assignment_id = aq.assignment_id
                                 AND a.user_id = ? AND a.score IS NOT NULL
                            WHERE aq.assignment_id = ? GROUP BY aq.question_id ORDER BY aq.position""", user_id, aid)
    total = len(rows)
    done = sum(1 for r in rows if r["tries"])
    best = [r["best"] or 0 for r in rows]
    return {"total": total, "done": done, "mastered": sum(1 for b in best if b >= 1),
            "score": round(sum(best) / total, 3) if total else 0, "questions": rows}


@router.get("/api/classes/:id/assignments")
def list_for_class(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    rows = db.all_(req.db, """SELECT a.id, a.title, a.day, a.created_at,
                                     (SELECT count(*) FROM assignment_questions x WHERE x.assignment_id = a.id) AS questions
                              FROM assignments a WHERE a.class_id = ? ORDER BY a.day DESC, a.id DESC""", cid)
    return json_response({"assignments": rows})


@router.post("/api/assignments")
def create(req):
    """Crée la séance pour une ou plusieurs classes (class_ids)."""
    user = security.require_staff(req)
    data = req.json
    title = require_str(data, "title", 200)
    day = _check_day(data.get("day"))
    qids = int_list(data, "question_ids")
    class_ids = int_list(data, "class_ids") if "class_ids" in data else [to_int(data.get("class_id"), "classe")]
    if not qids:
        raise HttpError(400, "Choisissez au moins une question")
    created = []
    with db.Tx(req.db):
        for cid in class_ids:
            security.require_class_access(req.db, user, cid)
            aid = db.insert(req.db, "INSERT INTO assignments(class_id, title, day, created_by, created_at) "
                                    "VALUES (?, ?, ?, ?, ?)", cid, title, day, user["id"], db.now())
            _set_questions(req.db, aid, cid, qids)
            created.append(aid)
    return json_response({"ids": created}, 201)


def _load(req):
    user = security.require_staff(req)
    aid = to_int(req.params["id"])
    a = db.one(req.db, "SELECT * FROM assignments WHERE id = ?", aid)
    if not a:
        raise HttpError(404, "Séance introuvable")
    security.require_class_access(req.db, user, a["class_id"])
    return a


@router.get("/api/assignments/:id")
def get(req):
    a = _load(req)
    a["questions"] = assignment_questions(req.db, a["id"])
    students = db.all_(req.db, """SELECT u.id, u.username, u.display_name FROM class_members m
                                  JOIN users u ON u.id = m.user_id
                                  WHERE m.class_id = ? AND u.role = 'student' ORDER BY u.display_name, u.username""",
                       a["class_id"])
    for s in students:
        s["progress"] = progress(req.db, a["id"], s["id"])
    a["students"] = students
    return json_response({"assignment": a})


@router.put("/api/assignments/:id")
def update(req):
    a = _load(req)
    data = req.json
    with db.Tx(req.db):
        if "title" in data:
            req.db.execute("UPDATE assignments SET title = ? WHERE id = ?", (require_str(data, "title", 200), a["id"]))
        if "day" in data:
            req.db.execute("UPDATE assignments SET day = ? WHERE id = ?", (_check_day(data["day"]), a["id"]))
        if "question_ids" in data:
            _set_questions(req.db, a["id"], a["class_id"], int_list(data, "question_ids"))
    return json_response({"ok": True})


@router.delete("/api/assignments/:id")
def delete(req):
    a = _load(req)
    req.db.execute("DELETE FROM assignments WHERE id = ?", (a["id"],))
    return json_response({"ok": True})
