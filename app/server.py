"""Serveur HTTP de QuestionnApp (bibliothèque standard uniquement).

Lancement : python3 run.py   (voir README.md pour les options)
"""

import mimetypes
import os
import secrets
import sys
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import api  # noqa: F401  (enregistre les routes)
from . import config, db, security
from .web import HttpError, Request, Response, json_response, router

MAX_BODY = 2 * 1024 * 1024
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data:; "
        "font-src 'self' data: https://cdnjs.cloudflare.com; connect-src 'self'; frame-ancestors 'none'"),
}


def handle(request):
    """Traite une requête API et renvoie une Response (utilisable sans serveur, ex. tests)."""
    conn = db.connect()
    try:
        request.db = conn
        if request.method not in ("GET", "HEAD") and request.headers.get("X-Requested-With") != "questionnapp":
            # protection CSRF : un site tiers ne peut pas poser cet en-tête sans pré-vol CORS
            raise HttpError(403, "En-tête X-Requested-With manquant")
        request.user = security.user_from_request(conn, request)
        func, params = router.match(request.method, request.path)
        request.params = params
        resp = func(request)
        return resp if isinstance(resp, Response) else json_response(resp)
    except HttpError as exc:
        return json_response({"error": exc.message, **exc.extra}, exc.status)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return json_response({"error": "Erreur interne du serveur"}, 500)
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "QuestionnApp"
    sys_version = ""

    def log_message(self, fmt, *args):
        if os.environ.get("QUESTIONNAPP_QUIET") != "1":
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, resp):
        self.send_response(resp.status)
        for k, v in {**SECURITY_HEADERS, **resp.headers}.items():
            self.send_header(k, v)
        for c in resp.cookies:
            self.send_header("Set-Cookie", c)
        self.send_header("Content-Length", str(len(resp.body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(resp.body)

    def _static(self, path):
        rel = path.lstrip("/") or "index.html"
        full = os.path.realpath(os.path.join(config.WEB_DIR, rel))
        if not full.startswith(os.path.realpath(config.WEB_DIR) + os.sep) or not os.path.isfile(full):
            full = os.path.join(config.WEB_DIR, "index.html")  # routage côté client
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            body = f.read()
        return Response(body, content_type=ctype, headers={"Cache-Control": "no-cache"})

    def _dispatch(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            if self.command not in ("GET", "HEAD"):
                return self._send(json_response({"error": "Méthode non autorisée"}, 405))
            return self._send(self._static(path))
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(json_response({"error": "Requête trop volumineuse"}, 413))
        body = self.rfile.read(length) if length else b""
        client_ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
        req = Request(self.command, path, urllib.parse.parse_qs(parsed.query), self.headers, body, client_ip)
        self._send(handle(req))

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _dispatch


def bootstrap():
    """Crée la base et, si elle est vide, un compte administrateur."""
    conn = db.connect()
    try:
        db.init(conn)
        from .api.banks import assign_missing_uids
        assign_missing_uids(conn)
        if not db.one(conn, "SELECT id FROM users LIMIT 1"):
            password = os.environ.get("QUESTIONNAPP_ADMIN_PASSWORD") or secrets.token_urlsafe(9)
            conn.execute("INSERT INTO users(username, password_hash, display_name, role, created_at) "
                         "VALUES ('admin', ?, 'Administrateur', 'admin', ?)",
                         (security.hash_password(password), db.now()))
            print("=" * 60)
            print(" Compte administrateur créé")
            print("   identifiant : admin")
            print(f"   mot de passe : {password}")
            print(" Changez-le après la première connexion.")
            print("=" * 60, flush=True)
    finally:
        conn.close()


def main():
    bootstrap()
    httpd = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    httpd.daemon_threads = True
    print(f"QuestionnApp sur http://{config.HOST}:{config.PORT}  (base : {config.DB_PATH})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


