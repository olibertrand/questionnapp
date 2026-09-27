"""Migration d'une base créée par une version antérieure."""

import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import db  # noqa: E402


class MigrationTest(unittest.TestCase):
    def test_old_attempts_table_gets_new_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
                CREATE TABLE attempts (id INTEGER PRIMARY KEY, user_id INTEGER, question_id INTEGER, version_id INTEGER,
                    assignment_id INTEGER, mode TEXT, seed INTEGER, fingerprint TEXT, instance TEXT, answers TEXT,
                    result TEXT, score REAL, created_at TEXT, answered_at TEXT);
                INSERT INTO attempts(user_id, question_id, version_id, mode, seed, fingerprint, instance, score, created_at)
                VALUES (1, 1, 1, 'free', 1, 'x', '{}', 1.0, '2026-01-01'), (1, 1, 1, 'free', 2, 'y', '{}', NULL, '2026-01-01');
            """)
            old.commit()
            old.close()
            conn = db.connect(path)
            db.init(conn)
            db.init(conn)  # idempotent
            rows = conn.execute("SELECT tries, history FROM attempts ORDER BY id").fetchall()
            conn.close()
        self.assertEqual([r["tries"] for r in rows], [1, 0])


class UidMigrationTest(unittest.TestCase):
    def test_existing_questions_get_uids(self):
        from app.api.banks import assign_missing_uids
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            conn = db.connect(path)
            db.init(conn)
            for title in ("Dictionnaires : parcours", "Dictionnaires : parcours", "Ma question"):
                conn.execute("INSERT INTO questions(title, created_at, updated_at) VALUES (?, 'x', 'x')", (title,))
            conn.execute("UPDATE questions SET uid = NULL")
            assign_missing_uids(conn)
            uids = [r["uid"] for r in conn.execute("SELECT uid FROM questions ORDER BY id")]
            conn.close()
        self.assertTrue(uids[0].startswith("DICO-"))  # identifiant de la banque (la plus ancienne)
        self.assertEqual(uids[1:], ["Q-0002", "Q-0003"])


if __name__ == "__main__":
    unittest.main()
