"""Séances : listes de questions données à une classe ou à une partie de la classe.

Deux sortes de séances :
  * datées (« dated ») : à traiter pour un jour donné ;
  * thématiques (« theme ») : sans date, un ensemble de questions choisi par le prof, actif
    jusqu'à ce qu'il le désactive.
Une séance s'adresse à toute la classe (aucun destinataire) ou à des groupes et/ou des élèves.
Une séance désactivée n'est plus visible des élèves (leurs réponses restent dans les statistiques).
"""

import datetime

from .. import db, security
from ..web import HttpError, int_list, json_response, require_str, router, to_int

KINDS = ("dated", "theme")

# Séances visibles par l'élève :u (actives, de ses classes, et qui le visent s'il y a des destinataires)
VISIBLE_SQL = """a.active = 1
    AND a.class_id IN (SELECT class_id FROM class_members WHERE user_id = :u)
    AND (NOT EXISTS (SELECT 1 FROM assignment_targets t WHERE t.assignment_id = a.id)
         OR EXISTS (SELECT 1 FROM assignment_targets t WHERE t.assignment_id = a.id
                    AND (t.user_id = :u OR t.group_id IN (SELECT group_id FROM group_members WHERE user_id = :u))))"""


def _check_day(day):
    try:
        return datetime.date.fromisoformat(day).isoformat()
    except (TypeError, ValueError):
        raise HttpError(400, "Date invalide (AAAA-MM-JJ)") from None


def is_visible(conn, aid, user_id):
    return bool(conn.execute(f"SELECT 1 FROM assignments a WHERE a.id = :a AND {VISIBLE_SQL}",
                             {"a": aid, "u": user_id}).fetchone())


def targets(conn, aid):
    """Destinataires : {"group_ids": [...], "user_ids": [...]} (listes vides = toute la classe)."""
    rows = db.all_(conn, "SELECT group_id, user_id FROM assignment_targets WHERE assignment_id = ?", aid)
    return {"group_ids": [r["group_id"] for r in rows if r["group_id"]],
            "user_ids": [r["user_id"] for r in rows if r["user_id"]]}


def audience(conn, a):
    """Élèves concernés par la séance `a` (ligne de la table assignments)."""
    t = targets(conn, a["id"])
    sql = """SELECT u.id, u.username, u.display_name FROM class_members m JOIN users u ON u.id = m.user_id
             WHERE m.class_id = ? AND u.role = 'student'"""
    args = [a["class_id"]]
    if t["group_ids"] or t["user_ids"]:
        gm = ",".join("?" * len(t["group_ids"])) or "NULL"
        um = ",".join("?" * len(t["user_ids"])) or "NULL"
        sql += f""" AND (u.id IN ({um}) OR u.id IN (SELECT user_id FROM group_members WHERE group_id IN ({gm})))"""
        args += t["user_ids"] + t["group_ids"]
    return db.all_(conn, sql + " ORDER BY u.display_name, u.username", *args)


def targets_label(conn, aid):
    """Résumé lisible des destinataires (« Toute la classe », « Groupe A, Alice Martin »)."""
    t = targets(conn, aid)
    if not t["group_ids"] and not t["user_ids"]:
        return "Toute la classe"
    names = [r["name"] for r in db.all_(conn, f"SELECT name FROM groups WHERE id IN ({','.join('?' * len(t['group_ids'])) or 'NULL'})",
                                        *t["group_ids"])]
    names += [r["n"] for r in db.all_(conn, f"""SELECT coalesce(nullif(display_name, ''), username) AS n FROM users
                                             WHERE id IN ({','.join('?' * len(t['user_ids'])) or 'NULL'})""", *t["user_ids"])]
    return ", ".join(names)


def _set_targets(conn, aid, class_id, data):
    group_ids = int_list(data, "group_ids") if "group_ids" in data else []
    user_ids = int_list(data, "user_ids") if "user_ids" in data else []
    for gid in group_ids:
        if not db.one(conn, "SELECT 1 FROM groups WHERE id = ? AND class_id = ?", gid, class_id):
            raise HttpError(400, "Groupe introuvable dans cette classe")
    for uid in user_ids:
        if not db.one(conn, """SELECT 1 FROM class_members m JOIN users u ON u.id = m.user_id
                               WHERE m.class_id = ? AND m.user_id = ? AND u.role = 'student'""", class_id, uid):
            raise HttpError(400, "Élève introuvable dans cette classe")
    conn.execute("DELETE FROM assignment_targets WHERE assignment_id = ?", (aid,))
    for gid in set(group_ids):
        conn.execute("INSERT INTO assignment_targets(assignment_id, group_id) VALUES (?, ?)", (aid, gid))
    for uid in set(user_ids):
        conn.execute("INSERT INTO assignment_targets(assignment_id, user_id) VALUES (?, ?)", (aid, uid))


def _set_questions(conn, aid, class_id, qids):
    conn.execute("DELETE FROM assignment_questions WHERE assignment_id = ?", (aid,))
    whole_class = not db.one(conn, "SELECT 1 FROM assignment_targets WHERE assignment_id = ?", aid)
    for pos, qid in enumerate(qids):
        if not db.one(conn, "SELECT id FROM questions WHERE id = ?", qid):
            raise HttpError(400, f"Question {qid} introuvable")
        conn.execute("INSERT OR IGNORE INTO assignment_questions(assignment_id, question_id, position) VALUES (?, ?, ?)",
                     (aid, qid, pos))
        # séance pour toute la classe : ses questions sont aussi affectées à la classe (entraînement) ;
        # séance pour certains élèves : seuls ceux-ci y ont accès (voir adaptive.available_questions)
        if whole_class:
            conn.execute("INSERT OR IGNORE INTO class_questions(class_id, question_id) VALUES (?, ?)", (class_id, qid))


def assignment_questions(conn, aid):
    return db.all_(conn, """SELECT q.id, q.uid, q.title, c.name AS chapter FROM assignment_questions aq
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
    rows = db.all_(req.db, """SELECT a.id, a.title, a.day, a.kind, a.active, a.created_at,
                                     (SELECT count(*) FROM assignment_questions x WHERE x.assignment_id = a.id) AS questions
                              FROM assignments a WHERE a.class_id = ?
                              ORDER BY a.active DESC, a.kind = 'theme' DESC, a.day DESC, a.id DESC""", cid)
    for r in rows:
        r["audience"] = targets_label(req.db, r["id"])
    return json_response({"assignments": rows})


@router.post("/api/assignments")
def create(req):
    """Crée la séance pour une ou plusieurs classes (class_ids). Destinataires facultatifs
    (group_ids, user_ids) : seulement pour une séance d'une seule classe."""
    user = security.require_staff(req)
    data = req.json
    title = require_str(data, "title", 200)
    kind = data.get("kind", "dated")
    if kind not in KINDS:
        raise HttpError(400, "Type de séance invalide")
    day = _check_day(data.get("day")) if kind == "dated" else db.today()
    qids = int_list(data, "question_ids")
    class_ids = int_list(data, "class_ids") if "class_ids" in data else [to_int(data.get("class_id"), "classe")]
    if not qids:
        raise HttpError(400, "Choisissez au moins une question")
    targeted = bool(data.get("group_ids") or data.get("user_ids"))
    if targeted and len(class_ids) != 1:
        raise HttpError(400, "Des destinataires particuliers ne peuvent être choisis que pour une seule classe")
    created = []
    with db.Tx(req.db):
        for cid in class_ids:
            security.require_class_access(req.db, user, cid)
            aid = db.insert(req.db, "INSERT INTO assignments(class_id, title, day, kind, created_by, created_at) "
                                    "VALUES (?, ?, ?, ?, ?, ?)", cid, title, day, kind, user["id"], db.now())
            if targeted:
                _set_targets(req.db, aid, cid, data)
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
    a["targets"] = targets(req.db, a["id"])
    a["audience"] = targets_label(req.db, a["id"])
    students = audience(req.db, a)
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
        if "kind" in data:
            if data["kind"] not in KINDS:
                raise HttpError(400, "Type de séance invalide")
            req.db.execute("UPDATE assignments SET kind = ? WHERE id = ?", (data["kind"], a["id"]))
        if "day" in data and data.get("kind", a["kind"]) == "dated":
            req.db.execute("UPDATE assignments SET day = ? WHERE id = ?", (_check_day(data["day"]), a["id"]))
        if "active" in data:
            req.db.execute("UPDATE assignments SET active = ? WHERE id = ?", (1 if data["active"] else 0, a["id"]))
        if "group_ids" in data or "user_ids" in data:
            _set_targets(req.db, a["id"], a["class_id"], data)
        if "question_ids" in data:
            _set_questions(req.db, a["id"], a["class_id"], int_list(data, "question_ids"))
    return json_response({"ok": True})


@router.delete("/api/assignments/:id")
def delete(req):
    a = _load(req)
    req.db.execute("DELETE FROM assignments WHERE id = ?", (a["id"],))
    return json_response({"ok": True})
