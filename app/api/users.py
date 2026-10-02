import re

from .. import db, security
from ..web import HttpError, json_response, opt_str, require_str, router, to_int

ROLES = ("admin", "teacher", "student")
USERNAME_RE = re.compile(r"^[a-z0-9._-]{2,50}$")


def _check_username(username):
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise HttpError(400, f"Identifiant « {username} » invalide (lettres minuscules, chiffres, . _ -)")
    return username


def _can_manage_role(actor, role):
    return security.is_admin(actor) or (actor["role"] == "teacher" and role == "student")


def create_user(conn, username, password, display_name, role):
    username = _check_username(username)
    if role not in ROLES:
        raise HttpError(400, "Rôle invalide")
    security.check_password_strength(password)
    if db.one(conn, "SELECT id FROM users WHERE username = ?", username):
        raise HttpError(409, f"L'identifiant « {username} » existe déjà")
    # un compte créé par un prof ou un admin devra changer son mot de passe à la première connexion
    return db.insert(conn, """INSERT INTO users(username, password_hash, display_name, role, created_at, must_change_password)
                              VALUES (?, ?, ?, ?, ?, 1)""",
                     username, security.hash_password(password), display_name.strip(), role, db.now())


@router.get("/api/users")
def list_users(req):
    actor = security.require_staff(req)
    role = req.arg("role")
    sql = """SELECT u.id, u.username, u.display_name, u.role, u.active, u.created_at, u.last_login_at,
                    (SELECT group_concat(c.name, ', ') FROM class_members m JOIN classes c ON c.id = m.class_id
                     WHERE m.user_id = u.id) AS classes
             FROM users u"""
    args = []
    if role:
        sql += " WHERE u.role = ?"
        args.append(role)
    users = db.all_(req.db, sql + " ORDER BY u.role, u.display_name, u.username", *args)
    if not security.is_admin(actor):
        users = [u for u in users if u["role"] != "admin"]
    return json_response({"users": users})


@router.post("/api/users")
def create(req):
    actor = security.require_staff(req)
    data = req.json
    role = data.get("role", "student")
    if not _can_manage_role(actor, role):
        raise HttpError(403, "Vous ne pouvez créer que des élèves")
    with db.Tx(req.db):
        uid = create_user(req.db, require_str(data, "username", 50), data.get("password") or "",
                          opt_str(data, "display_name", max_len=100), role)
        for cid in data.get("class_ids") or []:
            security.require_class_access(req.db, actor, to_int(cid))
            req.db.execute("INSERT OR IGNORE INTO class_members(class_id, user_id) VALUES (?, ?)", (cid, uid))
    return json_response({"id": uid}, 201)


@router.post("/api/users/import")
def import_users(req):
    """Import CSV : identifiant;mot de passe;nom affiché (séparateur ; , ou tabulation)."""
    actor = security.require_staff(req)
    data = req.json
    text = data.get("csv") or ""
    role = data.get("role", "student")
    if not _can_manage_role(actor, role):
        raise HttpError(403, "Vous ne pouvez créer que des élèves")
    class_id = data.get("class_id")
    if class_id:
        security.require_class_access(req.db, actor, to_int(class_id))
    created, errors = [], []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in re.split(r"[;\t,]", line)]
        if len(parts) < 2:
            errors.append(f"ligne {n} : au moins « identifiant;mot de passe » attendu")
            continue
        username, password = parts[0], parts[1]
        display = parts[2] if len(parts) > 2 else ""
        try:
            with db.Tx(req.db):
                existing = db.one(req.db, "SELECT id, role FROM users WHERE username = ?", username.lower())
                if existing and class_id and existing["role"] == role:
                    uid = existing["id"]  # déjà inscrit : on se contente de l'ajouter à la classe
                else:
                    uid = create_user(req.db, username, password, display, role)
                    created.append(username.lower())
                if class_id:
                    req.db.execute("INSERT OR IGNORE INTO class_members(class_id, user_id) VALUES (?, ?)",
                                   (class_id, uid))
        except HttpError as exc:
            errors.append(f"ligne {n} : {exc.message}")
    return json_response({"created": created, "errors": errors})


@router.patch("/api/users/:id")
def update(req):
    actor = security.require_staff(req)
    uid = to_int(req.params["id"])
    target = security.require_student_visibility(req.db, actor, uid)
    if not _can_manage_role(actor, target["role"]):
        raise HttpError(403, "Accès refusé")
    data = req.json
    with db.Tx(req.db):
        if "display_name" in data:
            req.db.execute("UPDATE users SET display_name = ? WHERE id = ?",
                           (opt_str(data, "display_name", max_len=100), uid))
        if data.get("password"):
            security.check_password_strength(data["password"])
            req.db.execute("UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                           (security.hash_password(data["password"]), uid))
            req.db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        if "active" in data:
            if uid == actor["id"]:
                raise HttpError(400, "Vous ne pouvez pas vous désactiver vous-même")
            req.db.execute("UPDATE users SET active = ? WHERE id = ?", (1 if data["active"] else 0, uid))
            req.db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        if "role" in data:
            if not security.is_admin(actor) or data["role"] not in ROLES:
                raise HttpError(403, "Changement de rôle refusé")
            if uid == actor["id"] and data["role"] != "admin":
                raise HttpError(400, "Vous ne pouvez pas retirer votre propre rôle d'administrateur")
            req.db.execute("UPDATE users SET role = ? WHERE id = ?", (data["role"], uid))
        if "username" in data:
            username = _check_username(require_str(data, "username", 50))
            other = db.one(req.db, "SELECT id FROM users WHERE username = ? AND id != ?", username, uid)
            if other:
                raise HttpError(409, "Identifiant déjà utilisé")
            req.db.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
    return json_response({"ok": True})


@router.delete("/api/users/:id")
def delete(req):
    actor = security.require_staff(req)
    uid = to_int(req.params["id"])
    target = security.require_student_visibility(req.db, actor, uid)
    if uid == actor["id"]:
        raise HttpError(400, "Vous ne pouvez pas supprimer votre propre compte")
    if not _can_manage_role(actor, target["role"]):
        raise HttpError(403, "Accès refusé")
    req.db.execute("DELETE FROM users WHERE id = ?", (uid,))
    return json_response({"ok": True})
