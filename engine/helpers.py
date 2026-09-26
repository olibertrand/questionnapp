"""Fonctions mises à disposition des auteurs de questions dans le code générateur.

Toutes les fonctions aléatoires utilisent le générateur seedé de l'instance :
une même graine redonne exactement la même question.
"""

import contextlib
import io
import math
import random as _random_module
import sqlite3
import string
import textwrap

PRENOMS = [
    "Alice", "Bilal", "Chloé", "David", "Emma", "Farid", "Gabriel", "Hugo", "Inès",
    "Jade", "Karim", "Léa", "Mehdi", "Nina", "Oscar", "Paul", "Rose", "Sami",
    "Théo", "Yasmine", "Zoé", "Lucas", "Manon", "Noah",
]
FRUITS = ["pomme", "poire", "kiwi", "banane", "mangue", "cerise", "fraise", "prune", "abricot", "orange"]
VILLES = ["Paris", "Lyon", "Lille", "Nantes", "Rennes", "Brest", "Nice", "Metz", "Dijon", "Tours", "Caen"]
NOMS_VARIABLES = ["a", "b", "c", "d", "i", "j", "k", "m", "n", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
NOMS_LISTES = ["L", "T", "tab", "liste", "valeurs", "nombres", "donnees", "t"]
NOMS_FONCTIONS = ["f", "g", "h", "mystere", "calcul", "traitement", "fonction", "secret"]


class ExecutionError(Exception):
    """Erreur levée par le code exécuté via run()/sql_run()."""


def _format_exc(exc):
    return f"{type(exc).__name__}: {exc}"


def run(code, inputs=None, namespace=None, max_output=20000):
    """Exécute du code Python et renvoie ce qu'il affiche (sans le dernier saut de ligne).

    inputs : liste de chaînes renvoyées successivement par input().
    """
    feed = list(inputs or [])
    out = io.StringIO()

    def fake_input(prompt=""):
        out.write(str(prompt))
        if not feed:
            raise ExecutionError("input() appelé mais aucune entrée n'est prévue")
        value = str(feed.pop(0))
        out.write(value + "\n")
        return value

    # si `namespace` est fourni, les variables du programme y restent accessibles après exécution
    ns = namespace if namespace is not None else {}
    ns.setdefault("__name__", "__main__")
    ns["input"] = fake_input
    with contextlib.redirect_stdout(out):
        exec(compile(textwrap.dedent(code), "<code>", "exec"), ns)
    text = out.getvalue()
    if len(text) > max_output:
        raise ExecutionError("sortie trop longue")
    return text[:-1] if text.endswith("\n") else text


def run_error(code, inputs=None):
    """Exécute du code et renvoie le nom de l'exception levée, ou None s'il n'y en a pas."""
    try:
        run(code, inputs)
    except Exception as exc:  # noqa: BLE001 - on veut justement le type d'erreur
        return type(exc).__name__
    return None


def evaluate(code, expression, inputs=None):
    """Exécute `code` puis renvoie la valeur de `expression` dans le même espace de noms."""
    ns = {"__name__": "__main__"}
    run(code, inputs, ns)
    return eval(expression, ns)


def sql_connect(setup):
    db = sqlite3.connect(":memory:")
    db.executescript(setup)
    return db


def sql_run(setup, query):
    """Exécute `setup` (script SQL) dans une base en mémoire puis renvoie les lignes de `query`."""
    db = sql_connect(setup)
    try:
        return [tuple(r) for r in db.execute(query).fetchall()]
    finally:
        db.close()


def sql_value(setup, query):
    """Première colonne de la première ligne du résultat (ou None)."""
    rows = sql_run(setup, query)
    return rows[0][0] if rows else None


def _md_cell(v):
    if v is None:
        return "NULL"
    return str(v).replace("|", "\\|").replace("\n", " ")


def md_table(rows, headers=None):
    """Tableau Markdown à partir d'une liste de lignes (tuples/listes)."""
    rows = [list(r) for r in rows]
    if headers is None:
        headers = [""] * (len(rows[0]) if rows else 0)
    lines = ["| " + " | ".join(_md_cell(h) for h in headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def sql_table(setup, table, limit=None):
    """Contenu d'une table (générée par `setup`) sous forme de tableau Markdown."""
    db = sql_connect(setup)
    try:
        cur = db.execute(f'SELECT * FROM "{table}"' + (f" LIMIT {int(limit)}" if limit else ""))
        headers = [d[0] for d in cur.description]
        return md_table(cur.fetchall(), headers)
    finally:
        db.close()


def sql_schema(setup):
    """Schéma relationnel lisible : table(col1, col2, ...) pour chaque table."""
    db = sql_connect(setup)
    try:
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        parts = []
        for t in tables:
            cols = []
            for _cid, name, _type, _nn, _dflt, pk in db.execute(f'PRAGMA table_info("{t}")'):
                cols.append(f"__{name}__" if pk else name)
            fks = {r[3]: (r[2], r[4]) for r in db.execute(f'PRAGMA foreign_key_list("{t}")')}
            cols = [c + (f" → {fks[c][0]}.{fks[c][1]}" if c in fks else "") for c in cols]
            parts.append(f"- **{t}**({', '.join(cols)})")
        return "\n".join(parts)
    finally:
        db.close()


def sql_quote(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def sql_insert(table, rows):
    """Script INSERT pour une liste de lignes."""
    return "\n".join(
        f"INSERT INTO {table} VALUES ({', '.join(sql_quote(v) for v in r)});" for r in rows)


def tobase(n, base, width=0):
    """Écriture de l'entier n en base 2..36 (chiffres en majuscules), complétée à `width` chiffres."""
    if not 2 <= base <= 36:
        raise ValueError("base entre 2 et 36")
    digits = string.digits + string.ascii_uppercase
    if n == 0:
        s = "0"
    else:
        neg, n, s = n < 0, abs(n), ""
        while n:
            n, r = divmod(n, base)
            s = digits[r] + s
        s = ("-" if neg else "") + s
    return s.rjust(width, "0")


def frombase(s, base):
    return int(str(s).replace(" ", ""), base)


def twos(n, bits):
    """Représentation en complément à deux de n sur `bits` bits."""
    if not -(1 << (bits - 1)) <= n < (1 << (bits - 1)):
        raise ValueError(f"{n} n'est pas représentable sur {bits} bits")
    return tobase(n & ((1 << bits) - 1), 2, bits)


def from_twos(s, bits=None):
    s = str(s).replace(" ", "")
    bits = bits or len(s)
    v = int(s, 2)
    return v - (1 << bits) if s[0] == "1" else v


def group(s, size=4, sep=" "):
    """Groupe les caractères par paquets depuis la droite : group('10110011') -> '1011 0011'."""
    s = str(s)
    head = len(s) % size
    parts = ([s[:head]] if head else []) + [s[i:i + size] for i in range(head, len(s), size)]
    return sep.join(parts)


def code_block(code, lang="python"):
    return f"```{lang}\n{textwrap.dedent(code).strip(chr(10))}\n```"


def indent(code, n=4):
    return textwrap.indent(textwrap.dedent(code), " " * n)


def dedent(code):
    return textwrap.dedent(code).strip("\n")


def fr(x, decimals=None):
    """Nombre au format français (virgule décimale)."""
    if decimals is not None:
        x = round(x, decimals)
        s = f"{x:.{decimals}f}"
    elif isinstance(x, float) and x.is_integer():
        s = str(int(x))
    else:
        s = str(x)
    return s.replace(".", ",")


def make_random_api(rng):
    """Fonctions aléatoires liées au générateur seedé `rng`."""

    def randint(a, b):
        return rng.randint(a, b)

    def randnz(a, b):
        """Entier aléatoire non nul entre a et b."""
        if a == 0 == b:
            raise ValueError("intervalle réduit à 0")
        while True:
            v = rng.randint(a, b)
            if v != 0:
                return v

    def choice(seq):
        return rng.choice(list(seq))

    def sample(seq, k):
        return rng.sample(list(seq), k)

    def shuffled(seq):
        items = list(seq)
        rng.shuffle(items)
        return items

    def randlist(n, a, b, distinct=False):
        """Liste de n entiers aléatoires dans [a, b] (distincts si demandé)."""
        if distinct:
            return rng.sample(range(a, b + 1), n)
        return [rng.randint(a, b) for _ in range(n)]

    def randword(length=None, alphabet=string.ascii_lowercase):
        length = length or rng.randint(4, 7)
        return "".join(rng.choice(alphabet) for _ in range(length))

    def randname(pool=None, k=None):
        pool = list(pool or NOMS_VARIABLES)
        return rng.choice(pool) if k is None else rng.sample(pool, k)

    def coin(p=0.5):
        return rng.random() < p

    return {
        "rng": rng, "random": rng, "randint": randint, "randnz": randnz, "choice": choice,
        "sample": sample, "shuffled": shuffled, "randlist": randlist, "randword": randword,
        "randname": randname, "coin": coin, "uniform": rng.uniform, "randrange": rng.randrange,
    }


STATIC_API = {
    "run": run, "run_error": run_error, "evaluate": evaluate, "ExecutionError": ExecutionError,
    "sql_run": sql_run, "sql_value": sql_value, "sql_table": sql_table, "sql_schema": sql_schema,
    "sql_insert": sql_insert, "sql_quote": sql_quote, "md_table": md_table,
    "tobase": tobase, "frombase": frombase, "twos": twos, "from_twos": from_twos, "group": group,
    "code_block": code_block, "indent": indent, "dedent": dedent, "fr": fr,
    "PRENOMS": PRENOMS, "FRUITS": FRUITS, "VILLES": VILLES, "NOMS_VARIABLES": NOMS_VARIABLES,
    "NOMS_LISTES": NOMS_LISTES, "NOMS_FONCTIONS": NOMS_FONCTIONS,
    "math": math, "string": string, "textwrap": textwrap,
}


def seed_global_random(seed):
    """Le module `random` global est aussi seedé : un `import random` reste déterministe."""
    _random_module.seed(seed)
