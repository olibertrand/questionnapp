"""Mots de passe, sessions et contrôle d'accès."""

import datetime
import hashlib
import hmac
import secrets
import threading
import time

from . import config, db
from .web import HttpError

# --- mots de passe (scrypt, format : scrypt$n$r$p$sel$hash) -------------------

_N, _R, _P = 2 ** 14, 8, 1


def hash_password(password):
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${h.hex()}"


def verify_password(password, stored):
    try:
        algo, n, r, p, salt, h = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                              n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(h)))
        return hmac.compare_digest(calc.hex(), h)
    except (ValueError, TypeError):
        return False


def check_password_strength(password):
    if not isinstance(password, str) or len(password) < 4:
        raise HttpError(400, "Le mot de passe doit contenir au moins 4 caractères")
    if len(password) > 200:
        raise HttpError(400, "Mot de passe trop long")


# --- sessions ------------------------------------------------------------------

COOKIE = "qa_session"


def _token_hash(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def create_session(conn, user_id):
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=config.SESSION_DAYS)
    conn.execute("INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                 (_token_hash(token), user_id, db.now(), expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")))
    return token


def session_cookie(token, max_age=None):
    max_age = config.SESSION_DAYS * 86400 if max_age is None else max_age
    parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Lax", f"Max-Age={max_age}"]
    if config.SECURE_COOKIES:
        parts.append("Secure")
    return "; ".join(parts)


def user_from_request(conn, request):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    row = db.one(conn, """
        SELECT u.id, u.username, u.display_name, u.role, u.active, u.must_change_password, s.expires_at
        FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?""", _token_hash(token))
    if not row or not row["active"] or row["expires_at"] < db.now():
        return None
    row.pop("expires_at")
    return row


def delete_session(conn, request):
    token = request.cookies.get(COOKIE)
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# --- limitation des tentatives de connexion -------------------------------------

_failures = {}
_lock = threading.Lock()
MAX_FAILURES, WINDOW = 8, 300


def throttle_check(key):
    with _lock:
        stamps = [t for t in _failures.get(key, []) if time.time() - t < WINDOW]
        _failures[key] = stamps
        if len(stamps) >= MAX_FAILURES:
            raise HttpError(429, "Trop de tentatives, réessayez dans quelques minutes")


def throttle_fail(key):
    with _lock:
        _failures.setdefault(key, []).append(time.time())


def throttle_reset(key):
    with _lock:
        _failures.pop(key, None)


# --- contrôle d'accès ------------------------------------------------------------

def require_user(request):
    if not request.user:
        raise HttpError(401, "Connexion requise")
    return request.user


def require_role(request, *roles):
    user = require_user(request)
    if user["role"] not in roles:
        raise HttpError(403, "Accès refusé")
    return user


def require_staff(request):
    return require_role(request, "admin", "teacher")


def is_admin(user):
    return user["role"] == "admin"


def teacher_class_ids(conn, user):
    """Classes gérables par l'utilisateur (toutes pour un admin)."""
    if is_admin(user):
        return {r["id"] for r in db.all_(conn, "SELECT id FROM classes")}
    return {r["class_id"] for r in db.all_(conn, "SELECT class_id FROM class_members WHERE user_id = ?", user["id"])}


def require_class_access(conn, user, class_id):
    if not db.one(conn, "SELECT id FROM classes WHERE id = ?", class_id):
        raise HttpError(404, "Classe introuvable")
    if is_admin(user):
        return
    if not db.one(conn, "SELECT 1 FROM class_members WHERE class_id = ? AND user_id = ?", class_id, user["id"]):
        raise HttpError(403, "Vous n'avez pas accès à cette classe")


def require_student_visibility(conn, user, student_id):
    """Un prof ne voit que les élèves de ses classes."""
    target = db.one(conn, "SELECT id, role FROM users WHERE id = ?", student_id)
    if not target:
        raise HttpError(404, "Utilisateur introuvable")
    if is_admin(user) or user["id"] == student_id:
        return target
    if user["role"] != "teacher":
        raise HttpError(403, "Accès refusé")
    if target["role"] != "student":
        raise HttpError(403, "Accès refusé")
    shared = db.one(conn, """
        SELECT 1 FROM class_members a JOIN class_members b ON a.class_id = b.class_id
        WHERE a.user_id = ? AND b.user_id = ?""", user["id"], student_id)
    if not shared:
        # un élève sans classe reste visible des profs (pour pouvoir l'inscrire)
        if db.one(conn, "SELECT 1 FROM class_members WHERE user_id = ?", student_id):
            raise HttpError(403, "Cet élève n'est pas dans vos classes")
    return target
