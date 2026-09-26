from .. import db, security
from ..web import HttpError, int_list, json_response, opt_str, require_str, router, to_int


@router.get("/api/classes")
def list_classes(req):
    user = security.require_user(req)
    sql = """SELECT c.id, c.name, c.description, c.created_at,
                (SELECT count(*) FROM class_members m JOIN users u ON u.id = m.user_id
                 WHERE m.class_id = c.id AND u.role = 'student') AS students,
                (SELECT group_concat(coalesce(nullif(u.display_name, ''), u.username), ', ')
                 FROM class_members m JOIN users u ON u.id = m.user_id
                 WHERE m.class_id = c.id AND u.role != 'student') AS teachers,
                (SELECT count(*) FROM class_questions q WHERE q.class_id = c.id) AS questions
             FROM classes c"""
    if security.is_admin(user):
        rows = db.all_(req.db, sql + " ORDER BY c.name")
    else:
        rows = db.all_(req.db, sql + " WHERE c.id IN (SELECT class_id FROM class_members WHERE user_id = ?)"
                                     " ORDER BY c.name", user["id"])
    return json_response({"classes": rows})


@router.post("/api/classes")
def create(req):
    user = security.require_staff(req)
    data = req.json
    with db.Tx(req.db):
        cid = db.insert(req.db, "INSERT INTO classes(name, description, created_by, created_at) VALUES (?, ?, ?, ?)",
                        require_str(data, "name", 100), opt_str(data, "description"), user["id"], db.now())
        if user["role"] == "teacher":
            req.db.execute("INSERT INTO class_members(class_id, user_id) VALUES (?, ?)", (cid, user["id"]))
    return json_response({"id": cid}, 201)


@router.get("/api/classes/:id")
def get(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    cls = db.one(req.db, "SELECT id, name, description, created_at FROM classes WHERE id = ?", cid)
    cls["members"] = db.all_(req.db, """
        SELECT u.id, u.username, u.display_name, u.role, u.last_login_at, u.active
        FROM class_members m JOIN users u ON u.id = m.user_id WHERE m.class_id = ?
        ORDER BY u.role DESC, u.display_name, u.username""", cid)
    cls["question_ids"] = [r["question_id"] for r in db.all_(
        req.db, "SELECT question_id FROM class_questions WHERE class_id = ?", cid)]
    return json_response({"class": cls})


@router.patch("/api/classes/:id")
def update(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    data = req.json
    if "name" in data:
        req.db.execute("UPDATE classes SET name = ? WHERE id = ?", (require_str(data, "name", 100), cid))
    if "description" in data:
        req.db.execute("UPDATE classes SET description = ? WHERE id = ?", (opt_str(data, "description"), cid))
    return json_response({"ok": True})


@router.delete("/api/classes/:id")
def delete(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    req.db.execute("DELETE FROM classes WHERE id = ?", (cid,))
    return json_response({"ok": True})


@router.post("/api/classes/:id/members")
def add_members(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    ids = int_list(req.json, "user_ids")
    with db.Tx(req.db):
        for uid in ids:
            target = db.one(req.db, "SELECT role FROM users WHERE id = ?", uid)
            if not target:
                raise HttpError(404, f"Utilisateur {uid} introuvable")
            if target["role"] != "student" and not security.is_admin(user):
                raise HttpError(403, "Seul un administrateur peut ajouter un professeur à une classe")
            req.db.execute("INSERT OR IGNORE INTO class_members(class_id, user_id) VALUES (?, ?)", (cid, uid))
    return json_response({"ok": True})


@router.delete("/api/classes/:id/members/:uid")
def remove_member(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    req.db.execute("DELETE FROM class_members WHERE class_id = ? AND user_id = ?", (cid, to_int(req.params["uid"])))
    return json_response({"ok": True})


@router.put("/api/classes/:id/questions")
def set_questions(req):
    """Remplace l'ensemble des questions affectées à la classe."""
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    ids = set(int_list(req.json, "question_ids"))
    with db.Tx(req.db):
        req.db.execute("DELETE FROM class_questions WHERE class_id = ?", (cid,))
        for qid in ids:
            if db.one(req.db, "SELECT id FROM questions WHERE id = ?", qid):
                req.db.execute("INSERT INTO class_questions(class_id, question_id) VALUES (?, ?)", (cid, qid))
    return json_response({"ok": True})
