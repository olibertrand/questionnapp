"""Chapitres et compétences."""

from .. import db, security
from ..web import HttpError, json_response, require_str, router, to_int


@router.get("/api/chapters")
def list_chapters(req):
    security.require_user(req)
    rows = db.all_(req.db, """
        SELECT c.id, c.name, c.position,
               (SELECT count(*) FROM questions q WHERE q.chapter_id = c.id AND q.archived = 0) AS questions
        FROM chapters c ORDER BY c.position, c.name""")
    return json_response({"chapters": rows})


@router.post("/api/chapters")
def create_chapter(req):
    security.require_staff(req)
    name = require_str(req.json, "name", 100)
    if db.one(req.db, "SELECT id FROM chapters WHERE name = ?", name):
        raise HttpError(409, "Ce chapitre existe déjà")
    pos = db.one(req.db, "SELECT coalesce(max(position), 0) + 1 AS p FROM chapters")["p"]
    cid = db.insert(req.db, "INSERT INTO chapters(name, position) VALUES (?, ?)", name, pos)
    return json_response({"id": cid}, 201)


@router.patch("/api/chapters/:id")
def update_chapter(req):
    security.require_staff(req)
    cid = to_int(req.params["id"])
    data = req.json
    if "name" in data:
        req.db.execute("UPDATE chapters SET name = ? WHERE id = ?", (require_str(data, "name", 100), cid))
    if "position" in data:
        req.db.execute("UPDATE chapters SET position = ? WHERE id = ?", (to_int(data["position"]), cid))
    return json_response({"ok": True})


@router.delete("/api/chapters/:id")
def delete_chapter(req):
    security.require_staff(req)
    req.db.execute("DELETE FROM chapters WHERE id = ?", (to_int(req.params["id"]),))
    return json_response({"ok": True})


@router.get("/api/skills")
def list_skills(req):
    security.require_user(req)
    rows = db.all_(req.db, """
        SELECT s.id, s.name, s.chapter_id, c.name AS chapter,
               (SELECT count(*) FROM question_skills qs WHERE qs.skill_id = s.id) AS questions
        FROM skills s LEFT JOIN chapters c ON c.id = s.chapter_id
        ORDER BY c.position, s.name""")
    return json_response({"skills": rows})


@router.patch("/api/skills/:id")
def update_skill(req):
    security.require_staff(req)
    sid = to_int(req.params["id"])
    data = req.json
    if "name" in data:
        req.db.execute("UPDATE skills SET name = ? WHERE id = ?", (require_str(data, "name", 150), sid))
    if "chapter_id" in data:
        req.db.execute("UPDATE skills SET chapter_id = ? WHERE id = ?", (data["chapter_id"], sid))
    return json_response({"ok": True})


@router.delete("/api/skills/:id")
def delete_skill(req):
    security.require_staff(req)
    req.db.execute("DELETE FROM skills WHERE id = ?", (to_int(req.params["id"]),))
    return json_response({"ok": True})
