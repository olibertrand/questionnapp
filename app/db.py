"""Accès SQLite (une connexion par requête HTTP)."""

import datetime
import os
import sqlite3

from . import config


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today():
    return datetime.date.today().isoformat()


def _dict_factory(cursor, row):
    return {d[0]: row[i] for i, d in enumerate(cursor.description)}


def connect(path=None):
    path = path or config.DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)  # autocommit, transactions explicites
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


# Colonnes ajoutées après la première version : (table, colonne, définition)
MIGRATIONS = [
    ("attempts", "tries", "INTEGER NOT NULL DEFAULT 0"),
    ("attempts", "history", "TEXT"),
    ("questions", "uid", "TEXT"),
]


def init(conn):
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    for table, column, definition in MIGRATIONS:
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            if (table, column) == ("attempts", "tries"):
                conn.execute("UPDATE attempts SET tries = 1 WHERE score IS NOT NULL")
    # identifiants des questions créées avant leur introduction (les questions de la banque
    # reçoivent ensuite leur identifiant officiel, voir banks.assign_missing_uids)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_uid ON questions(uid)")


class Tx:
    """Transaction : `with Tx(conn): ...` (COMMIT ou ROLLBACK automatique)."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, *_):
        self.conn.execute("ROLLBACK" if exc_type else "COMMIT")
        return False


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()


def all_(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def insert(conn, sql, *args):
    return conn.execute(sql, args).lastrowid
