"""Micro-framework HTTP : routage, requêtes, réponses, erreurs."""

import json
import re
import urllib.parse


class HttpError(Exception):
    def __init__(self, status, message, **extra):
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra


class Request:
    def __init__(self, method, path, query, headers, body, client_ip):
        self.method = method
        self.path = path
        self.query = query
        self.headers = headers
        self.raw_body = body
        self.client_ip = client_ip
        self.params = {}
        self.user = None
        self.db = None
        self.cookies = {}
        for part in (headers.get("Cookie") or "").split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                self.cookies[k] = v
        self._json = None

    @property
    def json(self):
        if self._json is None:
            if not self.raw_body:
                self._json = {}
            else:
                try:
                    self._json = json.loads(self.raw_body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    raise HttpError(400, "Corps JSON invalide") from None
            if not isinstance(self._json, (dict, list)):
                raise HttpError(400, "Corps JSON invalide")
        return self._json

    def arg(self, name, default=None):
        return self.query.get(name, [default])[0]

    def int_arg(self, name, default=None):
        v = self.arg(name)
        if v in (None, ""):
            return default
        try:
            return int(v)
        except ValueError:
            raise HttpError(400, f"Paramètre {name} invalide") from None


class Response:
    def __init__(self, body=b"", status=200, content_type="application/json; charset=utf-8", headers=None):
        self.status = status
        self.body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.headers.update(headers or {})
        self.cookies = []


def json_response(data, status=200):
    return Response(json.dumps(data, ensure_ascii=False, default=str), status)


class Router:
    def __init__(self):
        self.routes = []

    def route(self, method, pattern):
        regex = re.compile("^" + re.sub(r":(\w+)", r"(?P<\1>[^/]+)", pattern) + "$")

        def deco(func):
            self.routes.append((method, regex, func))
            return func
        return deco

    def get(self, p):
        return self.route("GET", p)

    def post(self, p):
        return self.route("POST", p)

    def put(self, p):
        return self.route("PUT", p)

    def patch(self, p):
        return self.route("PATCH", p)

    def delete(self, p):
        return self.route("DELETE", p)

    def match(self, method, path):
        allowed = False
        for m, regex, func in self.routes:
            mo = regex.match(path)
            if mo:
                if m == method:
                    params = {k: urllib.parse.unquote(v) for k, v in mo.groupdict().items()}
                    return func, params
                allowed = True
        if allowed:
            raise HttpError(405, "Méthode non autorisée")
        raise HttpError(404, "Ressource introuvable")


router = Router()


# --- validation des entrées --------------------------------------------------

def require_str(data, key, max_len=200, allow_empty=False):
    v = data.get(key)
    if not isinstance(v, str):
        raise HttpError(400, f"Champ « {key} » manquant")
    v = v.strip()
    if not v and not allow_empty:
        raise HttpError(400, f"Champ « {key} » vide")
    if len(v) > max_len:
        raise HttpError(400, f"Champ « {key} » trop long")
    return v


def opt_str(data, key, default="", max_len=2000):
    v = data.get(key, default)
    if v is None:
        return default
    if not isinstance(v, str):
        raise HttpError(400, f"Champ « {key} » invalide")
    if len(v) > max_len:
        raise HttpError(400, f"Champ « {key} » trop long")
    return v.strip()


def int_list(data, key):
    v = data.get(key, [])
    if not isinstance(v, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in v):
        raise HttpError(400, f"Champ « {key} » : liste d'entiers attendue")
    return v


def to_int(v, name="id"):
    try:
        return int(v)
    except (TypeError, ValueError):
        raise HttpError(400, f"{name} invalide") from None
