from .. import db, security
from ..web import HttpError, json_response, require_str, router


def public_user(u):
    return {"id": u["id"], "username": u["username"], "display_name": u["display_name"] or u["username"],
            "role": u["role"], "must_change_password": bool(u.get("must_change_password"))}


@router.post("/api/auth/login")
def login(req):
    data = req.json
    username = require_str(data, "username", 100).lower()
    password = data.get("password") or ""
    key = f"{req.client_ip}|{username}"
    security.throttle_check(key)
    user = db.one(req.db, "SELECT * FROM users WHERE username = ?", username)
    if not user or not user["active"] or not security.verify_password(password, user["password_hash"]):
        security.throttle_fail(key)
        raise HttpError(401, "Identifiant ou mot de passe incorrect")
    security.throttle_reset(key)
    now = db.now()
    with db.Tx(req.db):
        token = security.create_session(req.db, user["id"])
        req.db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user["id"]))
        req.db.execute("INSERT INTO logins(user_id, at, ip) VALUES (?, ?, ?)", (user["id"], now, req.client_ip))
        req.db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    resp = json_response({"user": public_user(user)})
    resp.cookies.append(security.session_cookie(token))
    return resp


@router.post("/api/auth/logout")
def logout(req):
    security.delete_session(req.db, req)
    resp = json_response({"ok": True})
    resp.cookies.append(security.session_cookie("", max_age=0))
    return resp


@router.get("/api/version")
def app_version(req):
    from .. import version
    return json_response(version.info())


@router.get("/api/auth/me")
def me(req):
    if not req.user:
        return json_response({"user": None})
    return json_response({"user": public_user(req.user)})


@router.post("/api/auth/password")
def change_password(req):
    user = security.require_user(req)
    data = req.json
    row = db.one(req.db, "SELECT password_hash, must_change_password FROM users WHERE id = ?", user["id"])
    # changement imposé à la première connexion : l'utilisateur vient de s'authentifier, on ne
    # redemande pas le mot de passe actuel (il peut d'ailleurs le reprendre à l'identique)
    if not row["must_change_password"] and not security.verify_password(data.get("current") or "", row["password_hash"]):
        raise HttpError(400, "Mot de passe actuel incorrect")
    security.check_password_strength(data.get("new"))
    req.db.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                   (security.hash_password(data["new"]), user["id"]))
    return json_response({"ok": True})
