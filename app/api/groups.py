"""Groupes personnalisés d'élèves dans une classe (pour donner une séance à une partie de la classe)."""

from .. import db, security
from ..web import HttpError, int_list, json_response, require_str, router, to_int


def _check_members(conn, class_id, user_ids):
    for uid in user_ids:
        if not db.one(conn, """SELECT 1 FROM class_members m JOIN users u ON u.id = m.user_id
                               WHERE m.class_id = ? AND m.user_id = ? AND u.role = 'student'""", class_id, uid):
            raise HttpError(400, "Un des élèves choisis n'est pas dans cette classe")


def _set_members(conn, gid, user_ids):
    conn.execute("DELETE FROM group_members WHERE group_id = ?", (gid,))
    for uid in set(user_ids):
        conn.execute("INSERT INTO group_members(group_id, user_id) VALUES (?, ?)", (gid, uid))


@router.get("/api/classes/:id/groups")
def list_groups(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    groups = db.all_(req.db, "SELECT id, name FROM groups WHERE class_id = ? ORDER BY name", cid)
    for g in groups:
        g["user_ids"] = [r["user_id"] for r in db.all_(req.db, "SELECT user_id FROM group_members WHERE group_id = ?", g["id"])]
    return json_response({"groups": groups})


@router.post("/api/classes/:id/groups")
def create_group(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    data = req.json
    name = require_str(data, "name", 100)
    ids = int_list(data, "user_ids")
    with db.Tx(req.db):
        _check_members(req.db, cid, ids)
        gid = db.insert(req.db, "INSERT INTO groups(class_id, name) VALUES (?, ?)", cid, name)
        _set_members(req.db, gid, ids)
    return json_response({"id": gid}, 201)


def _load(req):
    user = security.require_staff(req)
    g = db.one(req.db, "SELECT * FROM groups WHERE id = ?", to_int(req.params["id"]))
    if not g:
        raise HttpError(404, "Groupe introuvable")
    security.require_class_access(req.db, user, g["class_id"])
    return g


@router.put("/api/groups/:id")
def update_group(req):
    g = _load(req)
    data = req.json
    with db.Tx(req.db):
        if "name" in data:
            req.db.execute("UPDATE groups SET name = ? WHERE id = ?", (require_str(data, "name", 100), g["id"]))
        if "user_ids" in data:
            ids = int_list(data, "user_ids")
            _check_members(req.db, g["class_id"], ids)
            _set_members(req.db, g["id"], ids)
    return json_response({"ok": True})


@router.delete("/api/groups/:id")
def delete_group(req):
    g = _load(req)
    with db.Tx(req.db):
        # une séance qui ne visait que ce groupe ne doit pas devenir « toute la classe » : on la désactive
        orphans = db.all_(req.db, """SELECT DISTINCT t.assignment_id FROM assignment_targets t WHERE t.group_id = ?
                                     AND NOT EXISTS (SELECT 1 FROM assignment_targets o WHERE o.assignment_id = t.assignment_id
                                                     AND (o.group_id IS NOT ? ))""", g["id"], g["id"])
        for o in orphans:
            req.db.execute("UPDATE assignments SET active = 0 WHERE id = ?", (o["assignment_id"],))
        req.db.execute("DELETE FROM groups WHERE id = ?", (g["id"],))
    return json_response({"ok": True, "deactivated": len(orphans)})
