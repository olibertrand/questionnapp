"""Génération d'instances de questions et correction des réponses.

Un modèle (template) est un dict JSON :
{
  "code": "code Python générateur (utilise randint, choice, ...)",
  "statement": "énoncé Markdown avec des {{ expressions }}",
  "fields": [ {"type": "number" | "text" | "choice" | "code" | "sql", ...}, ... ],
  "solution": "correction Markdown avec des {{ expressions }} (facultatif)"
}
Voir docs/QUESTION_FORMAT.md pour la référence complète.
"""

import ast
import builtins
import contextlib
import copy
import hashlib
import io
import json
import math
import random
import re
import signal
import sqlite3
import traceback
import unicodedata

from . import helpers, sandbox

FIELD_TYPES = ("number", "text", "choice", "code", "sql")
MAX_RETRIES = 200


class TemplateError(Exception):
    """Erreur dans le modèle de question (à afficher au professeur)."""

    def __init__(self, message, where=None, line=None):
        super().__init__(message)
        self.where = where
        self.line = line

    def to_dict(self):
        return {"error": str(self), "where": self.where, "line": self.line}


class Retry(Exception):
    """Levée par reject()/require() pour tirer de nouvelles valeurs."""


class TimeLimit(Exception):
    pass


@contextlib.contextmanager
def time_limit(seconds):
    """Interrompt le code après `seconds` secondes (Unix uniquement, thread principal)."""
    if not hasattr(signal, "setitimer"):
        yield
        return

    def handler(signum, frame):
        raise TimeLimit(f"temps d'exécution dépassé ({seconds} s)")

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


# ---------------------------------------------------------------------------
# Génération
# ---------------------------------------------------------------------------

def _require(cond, *_):
    if not cond:
        raise Retry()


def _reject(*_):
    raise Retry()


def _user_line(exc, filename):
    """Numéro de ligne dans le code utilisateur `filename` où l'exception s'est produite."""
    if isinstance(exc, SyntaxError) and exc.filename == filename:
        return exc.lineno
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == filename:
            line = frame.lineno
    return line


def _fmt(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return str(value)


_INTERP = re.compile(r"\{\{(.+?)\}\}", re.S)


def render(text, ns, where):
    """Remplace chaque {{ expression }} par sa valeur évaluée dans `ns`."""
    if not text:
        return ""

    def repl(m):
        expr = m.group(1).strip()
        try:
            return _fmt(eval(compile(expr, "<expr>", "eval"), ns))
        except Retry:
            raise
        except Exception as exc:  # noqa: BLE001
            raise TemplateError(f"{{{{ {expr} }}}} : {type(exc).__name__}: {exc}", where) from None

    return _INTERP.sub(repl, text)


def _eval(expr, ns, where):
    if not isinstance(expr, str) or not expr.strip():
        raise TemplateError("expression manquante", where)
    try:
        return eval(compile(expr.strip(), "<expr>", "eval"), ns)
    except Retry:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TemplateError(f"« {expr.strip()} » : {type(exc).__name__}: {exc}", where) from None


def _run_generator(template, rng):
    ns = {"__name__": "__question__", "__builtins__": __builtins__}
    ns.update(helpers.STATIC_API)
    ns.update(helpers.make_random_api(rng))
    ns["require"] = _require
    ns["reject"] = _reject
    code = template.get("code") or ""
    try:
        compiled = compile(code, "<generateur>", "exec")
    except SyntaxError as exc:
        raise TemplateError(f"erreur de syntaxe : {exc.msg}", "code", exc.lineno) from None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compiled, ns)
    except Retry:
        raise
    except TimeLimit:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TemplateError(f"{type(exc).__name__}: {exc}", "code", _user_line(exc, "<generateur>")) from None
    return ns


def _choice_options(field, ns, where):
    opts = field.get("options")
    if isinstance(opts, str):
        raw = _eval(opts, ns, where)
        try:
            result = [(str(t), bool(c)) for t, c in raw]
        except (TypeError, ValueError):
            raise TemplateError("options doit donner une liste de couples (texte, correct)", where) from None
    elif isinstance(opts, list):
        result = []
        for i, o in enumerate(opts):
            text = render(str(o.get("text", "")), ns, f"{where}.options[{i}]")
            corr = o.get("correct", False)
            if isinstance(corr, str):
                corr = _eval(corr, ns, f"{where}.options[{i}].correct")
            result.append((text, bool(corr)))
    else:
        raise TemplateError("options manquantes", where)
    if len(result) < 2:
        raise TemplateError("un QCM doit proposer au moins deux options", where)
    if len({t.strip() for t, _ in result}) != len(result):
        raise Retry()  # deux options identiques : on retire des valeurs
    if not any(c for _, c in result):
        raise TemplateError("aucune option correcte", where)
    if not field.get("multiple") and sum(1 for _, c in result if c) != 1:
        raise TemplateError("QCM à réponse unique : il faut exactement une option correcte "
                            "(ou cocher « plusieurs réponses »)", where)
    return result


def _build(template, seed):
    """Construit (instance publique, données privées, espace de noms) pour une graine."""
    if not isinstance(template, dict):
        raise TemplateError("le modèle doit être un objet JSON")
    fields = template.get("fields") or []
    if not fields:
        raise TemplateError("il faut au moins un champ de réponse", "fields")
    rng = random.Random(seed)
    helpers.seed_global_random(seed)
    last_retry = None
    for _ in range(MAX_RETRIES):
        try:
            ns = _run_generator(template, rng)
            statement = render(template.get("statement", ""), ns, "statement")
            public_fields, private_fields = [], []
            for i, f in enumerate(fields):
                where = f"fields[{i}]"
                ftype = f.get("type")
                if ftype not in FIELD_TYPES:
                    raise TemplateError(f"type de champ inconnu : {ftype!r}", where)
                pub = {"type": ftype, "label": render(f.get("label", ""), ns, where + ".label")}
                priv = {}
                if ftype == "number":
                    pub["suffix"] = f.get("suffix", "")
                    val = _eval(f.get("answer"), ns, where + ".answer")
                    try:
                        priv["expected"] = float(val)
                    except (TypeError, ValueError):
                        raise TemplateError(f"la réponse doit être un nombre (obtenu {val!r})", where) from None
                elif ftype == "text":
                    pub["multiline"] = bool(f.get("multiline"))
                    val = _eval(f.get("answer"), ns, where + ".answer")
                    accepted = [str(v) for v in val] if isinstance(val, (list, tuple, set)) else [_fmt(val)]
                    if not accepted:
                        raise TemplateError("aucune réponse acceptée", where)
                    priv["accepted"] = accepted
                elif ftype == "choice":
                    options = _choice_options(f, ns, where)
                    if f.get("shuffle", True):
                        rng.shuffle(options)
                    pub["options"] = [t for t, _ in options]
                    pub["multiple"] = bool(f.get("multiple"))
                    priv["correct"] = [i for i, (_, c) in enumerate(options) if c]
                elif ftype == "code":
                    pub["starter"] = render(f.get("starter", ""), ns, where + ".starter")
                    pub["language"] = "python"
                    if f.get("reference"):
                        priv["reference"] = render(f["reference"], ns, where + ".reference")
                elif ftype == "sql":
                    pub["language"] = "sql"
                    pub["starter"] = render(f.get("starter", ""), ns, where + ".starter")
                    priv["setup"] = str(_eval(f.get("setup"), ns, where + ".setup"))
                    priv["query"] = str(_eval(f.get("answer"), ns, where + ".answer"))
                    try:
                        helpers.sql_run(priv["setup"], priv["query"])
                    except sqlite3.Error as exc:
                        raise TemplateError(f"requête de référence invalide : {exc}", where) from None
                public_fields.append(pub)
                private_fields.append(priv)
            solution = render(template.get("solution", ""), ns, "solution")
            public = {"statement": statement, "fields": public_fields}
            return public, {"fields": private_fields, "solution": solution}, ns
        except Retry as r:
            last_retry = r
            continue
    raise TemplateError(f"impossible de satisfaire les contraintes (require/reject) après {MAX_RETRIES} essais",
                        "code") from last_retry


def fingerprint(public):
    data = json.dumps(public, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def generate(template, seed, avoid=(), max_tries=25):
    """Instance publique pour `seed`. Si son empreinte figure dans `avoid`, on essaie
    d'autres graines (au plus `max_tries`) pour proposer des données jamais vues."""
    avoid = set(avoid or ())
    picker = random.Random(seed ^ 0x5EED)
    best = None
    for _ in range(max(1, max_tries)):
        with time_limit(5):
            public, _priv, _ns = _build(template, seed)
        fp = fingerprint(public)
        if best is None:
            best = (seed, public, fp)
        if fp not in avoid:
            return {"seed": seed, "fingerprint": fp, "public": public, "fresh": True}
        seed = picker.getrandbits(32)
    seed, public, fp = best
    return {"seed": seed, "fingerprint": fp, "public": public, "fresh": False}


def expected_display(field, pub, priv):
    t = field.get("type")
    if t == "number":
        return helpers.fr(priv["expected"]) if not priv["expected"].is_integer() else str(int(priv["expected"]))
    if t == "text":
        v = priv["accepted"][0]
        return helpers.code_block(v, "text") if "\n" in v or pub.get("multiline") else f"`{v}`"
    if t == "choice":
        return "\n".join(f"- {pub['options'][i]}" for i in priv["correct"])
    if t == "sql":
        return helpers.code_block(priv["query"], "sql")
    return None


def preview(template, seed, samples=30):
    """Pour l'éditeur : instance + réponses attendues + indicateur de variété."""
    with time_limit(8):
        public, priv, _ns = _build(template, seed)
        public2, _, _ = _build(template, seed)
    deterministic = fingerprint(public) == fingerprint(public2)
    expected = [expected_display(f, p, q) for f, p, q in zip(template["fields"], public["fields"], priv["fields"])]
    seen = set()
    rng = random.Random(seed)
    try:
        with time_limit(6):
            for _ in range(samples):
                pub, _, _ = _build(template, rng.getrandbits(32))
                seen.add(fingerprint(pub))
    except TimeLimit:
        pass
    return {
        "seed": seed, "fingerprint": fingerprint(public), "public": public, "expected": expected,
        "solution": priv["solution"], "variety": {"samples": samples, "distinct": len(seen)},
        "deterministic": deterministic,
    }


# ---------------------------------------------------------------------------
# Correction
# ---------------------------------------------------------------------------

_NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$", re.I)


def parse_number(text):
    s = str(text).strip().replace("−", "-").replace(" ", "").replace(" ", "").replace(",", ".")
    if "/" in s:
        num, _, den = s.partition("/")
        if _NUM.match(num) and _NUM.match(den) and float(den) != 0:
            return float(num) / float(den)
        return None
    return float(s) if _NUM.match(s) else None


def _normalize_text(s, field):
    s = str(s).replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.split("\n")).strip("\n").strip()
    if field.get("ignore_case"):
        s = s.casefold()
    if field.get("ignore_accents"):
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    if field.get("ignore_spaces"):
        s = re.sub(r"\s+", "", s)
    else:
        s = re.sub(r"[ \t]+", " ", s)
    return s


def _check_number(field, priv, answer):
    value = parse_number(answer if answer is not None else "")
    if value is None:
        return 0.0, "Réponse non reconnue comme un nombre."
    exp = priv["expected"]
    tol = float(field.get("tolerance") or 0)
    ok = abs(value - exp) <= max(tol, 1e-9 * max(1.0, abs(exp)))
    return (1.0 if ok else 0.0), None


def _check_text(field, priv, answer):
    got = _normalize_text(answer or "", field)
    ok = any(got == _normalize_text(a, field) for a in priv["accepted"])
    return (1.0 if ok else 0.0), None


def _check_choice(field, pub, priv, answer):
    if answer is None or answer == "":
        chosen = set()
    elif isinstance(answer, list):
        chosen = {int(a) for a in answer}
    else:
        chosen = {int(answer)}
    correct = set(priv["correct"])
    if not field.get("multiple"):
        return (1.0 if chosen == correct else 0.0), None
    n = len(pub["options"])
    if chosen == correct:
        return 1.0, None
    # QCM multiple : score partiel = proportion d'options bien (dé)cochées, 0 si aucune cochée
    good = sum(1 for i in range(n) if (i in chosen) == (i in correct))
    return (round(good / n, 3) if chosen else 0.0), None


# Attributs « magiques » autorisés dans le code élève (programmation objet courante).
_SAFE_DUNDERS = {
    "__init__", "__str__", "__repr__", "__len__", "__eq__", "__ne__", "__lt__", "__le__", "__gt__",
    "__ge__", "__add__", "__sub__", "__mul__", "__truediv__", "__floordiv__", "__mod__", "__pow__",
    "__neg__", "__iter__", "__next__", "__contains__", "__getitem__", "__setitem__", "__delitem__",
    "__hash__", "__bool__", "__call__", "__name__", "__doc__", "__main__",
}
# Noms donnant accès à l'interpréteur (ex. typing.sys, collections.abc.sys).
_ESCAPE_NAMES = {"sys", "os", "builtins", "modules", "subprocess", "importlib", "gc", "inspect", "ctypes",
                 "posix", "nt", "signal", "resource", "sandbox", "engine", "helpers", "core"}
_STUDENT_IMPORTS = sandbox.ALLOWED_IMPORTS - {"sqlite3", "json", "time", "datetime", "abc", "numbers", "pprint"}


def _escape_usage(tree):
    """Constructions permettant de sortir du cadre de l'exercice (lecture de la correction...)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            a = node.attr
            if a in _ESCAPE_NAMES or (a.startswith("__") and a not in _SAFE_DUNDERS):
                return f"`.{a}`"
            if a.startswith("_") and not a.startswith("__") and not (isinstance(node.value, ast.Name) and node.value.id in ("self", "cls")):
                return f"`.{a}`"
        elif isinstance(node, ast.Name) and node.id.startswith("__") and node.id not in _SAFE_DUNDERS:
            return f"`{node.id}`"
        elif isinstance(node, ast.ImportFrom):
            if any(al.name.startswith("_") or al.name in _ESCAPE_NAMES for al in node.names):
                return "cet import"
    return None


def _student_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in _STUDENT_IMPORTS:
        raise ImportError(f"le module « {name} » n'est pas disponible dans cet exercice")
    return builtins.__import__(name, globals, locals, fromlist, level)


def _student_getattr(obj, name, *default):
    if not isinstance(name, str) or name.startswith("_") or name in _ESCAPE_NAMES:
        raise AttributeError(f"accès à l'attribut « {name} » interdit")
    return getattr(obj, name, *default)


def _student_builtins():
    b = dict(builtins.__dict__)
    for name in ("eval", "exec", "compile", "open", "breakpoint", "help", "globals", "vars", "memoryview",
                 "__loader__", "__spec__"):
        b.pop(name, None)
    b["__import__"] = _student_import
    b["getattr"] = _student_getattr

    def no_input(prompt=""):
        raise helpers.ExecutionError("input() n'est pas utilisable dans cet exercice")

    b["input"] = no_input
    return b


@contextlib.contextmanager
def _student_mode():
    sandbox.STUDENT = True
    try:
        yield
    finally:
        sandbox.STUDENT = False


def _forbidden_usage(tree, forbid):
    names = set(forbid or ())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in names:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in names:
            found.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name.split(".")[0] in names or "import" in names:
                    found.add(alias.name)
        elif isinstance(node, (ast.For, ast.While)) and ("for" in names or "while" in names):
            kw = "for" if isinstance(node, ast.For) else "while"
            if kw in names:
                found.add(kw)
    return sorted(found)


_PLAIN = (int, float, complex, str, bytes, bool, type(None))


def same_value(got, expected):
    """Égalité stricte qui ne fait pas confiance aux __eq__ définis par l'élève."""
    if isinstance(expected, bool) or isinstance(got, bool):
        return type(got) is type(expected) and got == expected
    if isinstance(expected, (int, float)) and type(got) in (int, float):
        return got == expected or math.isclose(got, expected, rel_tol=1e-9, abs_tol=1e-9)
    if type(got) is not type(expected):
        return False
    if isinstance(expected, _PLAIN):
        return got == expected
    if isinstance(expected, (list, tuple)):
        return len(got) == len(expected) and all(same_value(a, b) for a, b in zip(got, expected))
    if isinstance(expected, dict):
        return (set(got.keys()) == set(expected.keys())
                and all(same_value(got[k], expected[k]) for k in expected))
    if isinstance(expected, (set, frozenset)):
        return all(type(x) in _PLAIN or isinstance(x, tuple) for x in got) and got == expected
    return expected == got


def _short(v, limit=120):
    s = repr(v)
    return s if len(s) <= limit else s[:limit] + "…"


def _check_code(field, ns, answer):
    code = str(answer or "")
    if not code.strip():
        return 0.0, "Aucun code fourni."
    try:
        tree = ast.parse(code, "<eleve>")
    except SyntaxError as exc:
        return 0.0, f"Erreur de syntaxe ligne {exc.lineno} : {exc.msg}"
    bad = _forbidden_usage(tree, field.get("forbid"))
    if bad:
        return 0.0, "Utilisation interdite dans cet exercice : " + ", ".join(f"`{b}`" for b in bad)
    escape = _escape_usage(tree)
    if escape:
        return 0.0, f"Construction non autorisée dans les exercices : {escape}"

    student_ns = {"__name__": "__main__", "__builtins__": _student_builtins()}
    out = io.StringIO()
    limit = float(field.get("time_limit") or 2)
    try:
        with contextlib.redirect_stdout(out), time_limit(limit), _student_mode():
            exec(compile(tree, "<eleve>", "exec"), student_ns)
    except TimeLimit as exc:
        return 0.0, f"Votre programme ne s'arrête pas : {exc}."
    except helpers.ExecutionError as exc:
        return 0.0, str(exc)
    except BaseException as exc:  # noqa: BLE001 - y compris SystemExit
        line = _user_line(exc, "<eleve>")
        return 0.0, f"Erreur à l'exécution{f' ligne {line}' if line else ''} : {type(exc).__name__}: {exc}"

    results = []  # (ok, message)
    test_ns = dict(ns)
    test_ns.update({k: v for k, v in student_ns.items() if not k.startswith("__")})
    test_ns["student"] = student_ns
    test_ns["student_output"] = out.getvalue()

    def check(cond, message="test"):
        results.append((bool(cond), str(message)))
        return bool(cond)

    def check_equal(got, expected, message=None):
        ok = same_value(got, expected)
        results.append((ok, message or (f"obtenu {_short(got)}, attendu {_short(expected)}")))
        return ok

    test_ns["check"] = check
    test_ns["check_equal"] = check_equal

    try:
        with contextlib.redirect_stdout(io.StringIO()), time_limit(max(limit * 3, 3)), _student_mode():
            fname = field.get("function")
            if fname:
                func = student_ns.get(fname)
                if not callable(func):
                    return 0.0, f"La fonction `{fname}` n'est pas définie."
                cases = _eval(field.get("cases"), ns, "cases") if field.get("cases") else []
                for args, expected in cases:
                    args = args if isinstance(args, tuple) else (args,)
                    shown = f"{fname}({', '.join(_short(a, 60) for a in args)})"
                    try:
                        got = func(*copy.deepcopy(args))
                    except TimeLimit:
                        raise
                    except BaseException as exc:  # noqa: BLE001
                        results.append((False, f"`{shown}` lève {type(exc).__name__}: {exc}"))
                        continue
                    ok = same_value(got, expected)
                    results.append((ok, f"`{shown}` renvoie `{_short(got)}`" + ("" if ok else f", attendu `{_short(expected)}`")))
            if field.get("tests"):
                try:
                    exec(compile(field["tests"], "<tests>", "exec"), test_ns)
                except TimeLimit:
                    raise
                except AssertionError as exc:
                    results.append((False, str(exc) or f"assertion ligne {_user_line(exc, '<tests>')}"))
                except BaseException as exc:  # noqa: BLE001
                    results.append((False, f"erreur pendant les tests : {type(exc).__name__}: {exc}"))
    except TimeLimit as exc:
        results.append((False, f"Trop lent : {exc}."))

    if not results:
        return 1.0, "Code exécuté sans erreur."
    passed = sum(1 for ok, _ in results if ok)
    lines = [f"{passed}/{len(results)} test(s) réussi(s)."]
    shown = [m for ok, m in results if not ok][:5] if field.get("show_tests", True) else []
    lines += [f"- ✗ {m}" for m in shown]
    score = passed / len(results)
    if field.get("all_or_nothing"):
        score = 1.0 if passed == len(results) else 0.0
    return round(score, 3), "\n".join(lines)


def _norm_cell(v):
    if isinstance(v, float):
        return round(v, 6)
    return v


def _check_sql(field, priv, answer):
    query = str(answer or "").strip().rstrip(";").strip()
    if not query:
        return 0.0, "Aucune requête fournie."
    try:
        db = helpers.sql_connect(priv["setup"])
    except sqlite3.Error as exc:
        return 0.0, f"Base de l'exercice invalide : {exc}"
    def authorizer(action, *_):
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    try:
        with time_limit(3):
            db.set_authorizer(authorizer)
            cur = db.execute(query)
            db.set_authorizer(None)
            got = cur.fetchmany(5001)
            headers = [d[0] for d in (cur.description or [])]
            exp_cur = db.execute(priv["query"])
            expected = exp_cur.fetchall()
            exp_ncols = len(exp_cur.description or [])
    except TimeLimit:
        return 0.0, "Requête trop longue."
    except sqlite3.Error as exc:
        return 0.0, f"Erreur SQL : {exc}"
    except sqlite3.Warning as exc:
        return 0.0, f"Erreur SQL : {exc}"
    finally:
        db.close()
    got_n = [tuple(_norm_cell(c) for c in r) for r in got]
    exp_n = [tuple(_norm_cell(c) for c in r) for r in expected]
    if field.get("ordered"):
        ok = got_n == exp_n
    else:
        key = lambda r: json.dumps(r, default=str)  # noqa: E731
        ok = sorted(got_n, key=key) == sorted(exp_n, key=key)
    preview = helpers.md_table(got[:8], headers) if headers else "(aucun résultat)"
    more = f"\n\n… {len(got) - 8} ligne(s) de plus" if len(got) > 8 else ""
    msg = f"Votre requête renvoie {len(got)} ligne(s) et {len(headers)} colonne(s)."
    if not ok:
        hints = []
        if len(headers) != exp_ncols:
            hints.append(f"le nombre de colonnes attendu est {exp_ncols}")
        if len(got) != len(expected):
            hints.append(f"le nombre de lignes attendu est {len(expected)}")
        elif field.get("ordered") and sorted(got_n, key=str) == sorted(exp_n, key=str):
            hints.append("les lignes sont bonnes mais pas dans le bon ordre")
        if hints:
            msg += " Indice : " + ", ".join(hints) + "."
    return (1.0 if ok else 0.0), msg + "\n\n" + preview + more


def check(template, seed, answers):
    """Corrige `answers` (liste alignée sur les champs) pour l'instance de graine `seed`."""
    with time_limit(8):
        public, priv, ns = _build(template, seed)
    answers = list(answers or [])
    fields_out = []
    total = 0.0
    for i, (f, pub, prv) in enumerate(zip(template["fields"], public["fields"], priv["fields"])):
        ans = answers[i] if i < len(answers) else None
        t = f["type"]
        if t == "number":
            score, fb = _check_number(f, prv, ans)
        elif t == "text":
            score, fb = _check_text(f, prv, ans)
        elif t == "choice":
            try:
                score, fb = _check_choice(f, pub, prv, ans)
            except (TypeError, ValueError):
                score, fb = 0.0, "Réponse invalide."
        elif t == "code":
            score, fb = _check_code(f, ns, ans)
        else:
            score, fb = _check_sql(f, prv, ans)
        total += score
        fields_out.append({
            "score": score, "correct": score >= 1.0, "feedback": fb,
            "expected": expected_display(f, pub, prv),
        })
    score = round(total / len(fields_out), 3) if fields_out else 0.0
    return {"score": score, "correct": score >= 1.0, "fields": fields_out, "solution": priv["solution"],
            "fingerprint": fingerprint(public)}


# ---------------------------------------------------------------------------
# Auto-test d'un modèle (import, questions produites par une IA...)
# ---------------------------------------------------------------------------

_PY_BLOCK = re.compile(r"```python\n(.*?)```", re.S)


def reference_answers(template, public, priv):
    """Réponses « parfaites » d'une instance ; pour un champ `code`, le code de référence est
    `reference` (clé du champ, avec {{ }}) ou, à défaut, le premier bloc ```python de la correction."""
    answers, missing = [], []
    for i, (f, pub, prv) in enumerate(zip(template["fields"], public["fields"], priv["fields"])):
        t = f["type"]
        if t == "number":
            answers.append(repr(prv["expected"]))
        elif t == "text":
            answers.append(prv["accepted"][0])
        elif t == "choice":
            answers.append(prv["correct"] if f.get("multiple") else prv["correct"][0])
        elif t == "sql":
            answers.append(prv["query"])
        else:
            code = prv.get("reference")
            if not code:
                m = _PY_BLOCK.search(priv["solution"] or "")
                code = m.group(1) if m else None
            if not code:
                missing.append(i)
            answers.append(code or "")
    return answers, missing


def selftest(template, samples=20, base_seed=12345):
    """Vérifie un modèle sur `samples` graines : génération sans erreur, variété, réponse de
    référence acceptée, tests de code non triviaux. Renvoie un rapport (jamais d'exception)."""
    errors, warnings = [], []
    fps, fields_ok = set(), True
    rng = random.Random(base_seed)
    seeds = [rng.getrandbits(32) for _ in range(samples)]
    empty_sql = 0
    code_fields = [i for i, f in enumerate(template.get("fields") or []) if isinstance(f, dict) and f.get("type") == "code"]
    missing_ref = set()
    trivial_passes = set()
    done = 0
    try:
        with time_limit(40):
            for seed in seeds:
                try:
                    public, priv, _ns = _build(template, seed)
                except TemplateError as exc:
                    errors.append({"seed": seed, **exc.to_dict()})
                    if len(errors) >= 3:
                        break
                    continue
                fps.add(fingerprint(public))
                answers, missing = reference_answers(template, public, priv)
                missing_ref.update(missing)
                for f, prv in zip(template["fields"], priv["fields"]):
                    if f["type"] == "sql" and not helpers.sql_run(prv["setup"], prv["query"]):
                        empty_sql += 1
                result = check(template, seed, answers)
                for i, fr in enumerate(result["fields"]):
                    if i in missing:
                        continue
                    if not fr["correct"] and len(errors) < 5:
                        fields_ok = False
                        errors.append({"seed": seed, "where": f"fields[{i}]",
                                       "error": "la réponse de référence est refusée : " + (fr["feedback"] or "réponse incorrecte")})
                # un code qui ne fait rien ne doit pas passer les tests
                for i in code_fields:
                    f = template["fields"][i]
                    fname = f.get("function")
                    dummy = f"def {fname}(*args, **kwargs):\n    return None\n" if fname else "pass\n"
                    probe = list(answers)
                    probe[i] = dummy
                    if check(template, seed, probe)["fields"][i]["correct"]:
                        trivial_passes.add(i)
                done += 1
    except TimeLimit:
        warnings.append(f"auto-test interrompu (trop long) après {done} tirage(s)")
    for i in sorted(missing_ref):
        warnings.append(f"fields[{i}] : pas de code de référence (clé « reference » ou bloc ```python dans la correction) : "
                        "les tests n'ont pas pu être vérifiés")
    for i in sorted(trivial_passes):
        warnings.append(f"fields[{i}] : les tests acceptent une fonction qui ne fait rien")
    if done and empty_sql >= done / 2:
        warnings.append("la requête de référence renvoie souvent un résultat vide")
    if done and len(fps) < min(5, done) and not code_fields:
        warnings.append(f"peu de variété : {len(fps)} énoncé(s) différent(s) sur {done} tirages")
    status = "error" if errors else ("warning" if warnings else "ok")
    return {"status": status, "samples": done, "distinct": len(fps), "errors": errors, "warnings": warnings,
            "reference_ok": fields_ok and not errors}
