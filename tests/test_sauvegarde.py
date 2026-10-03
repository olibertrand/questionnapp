"""Sauvegarde et restauration de la base (scripts/sauvegarde.py et scripts/restaurer.py)."""

import datetime
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config, db  # noqa: E402
from scripts import restaurer, sauvegarde  # noqa: E402


def make_db(path, n_users=3):
    conn = db.connect(path)
    db.init(conn)
    for i in range(n_users):
        conn.execute("INSERT INTO users(username, password_hash, role, created_at) VALUES (?, 'x', 'student', 'x')",
                     (f"e{i}",))
    return conn


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.db_path = os.path.join(self.dir, "app.db")
        self.backups = os.path.join(self.dir, "sauvegardes")

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_while_database_is_open(self):
        conn = make_db(self.db_path)  # connexion ouverte, mode WAL, comme le serveur en marche
        path, counts = sauvegarde.backup(self.db_path, self.backups)
        conn.close()
        self.assertTrue(os.path.exists(path))
        self.assertEqual(counts["users"], 3)
        self.assertFalse([f for f in os.listdir(self.backups) if f.endswith(".partiel")])

    def test_damaged_copy_is_detected(self):
        bad = os.path.join(self.dir, "abime.db")
        with open(bad, "wb") as f:
            f.write(b"ceci n'est pas une base")
        with self.assertRaises(Exception):
            sauvegarde.summary(bad)

    def test_rotation_keeps_days_and_months(self):
        os.makedirs(self.backups)
        start = datetime.datetime(2026, 1, 1, 2, 0, 0)
        for d in range(400):  # plus d'un an de sauvegardes quotidiennes, deux par jour
            for h in (2, 14):
                t = start + datetime.timedelta(days=d, hours=h - 2)
                open(os.path.join(self.backups, f"questionnapp-{t:%Y-%m-%d_%H%M%S}.db"), "w").close()
        open(os.path.join(self.backups, "notes.txt"), "w").close()  # fichier étranger : jamais supprimé
        sauvegarde.rotate(self.backups, keep_days=14, keep_months=12)
        left = sorted(f for f in os.listdir(self.backups) if f.endswith(".db"))
        days = {f[13:23] for f in left}
        months = {f[13:20] for f in left}
        self.assertEqual(len(months), 12)
        self.assertEqual(len(left), len(days))  # une seule copie par jour (la plus récente)
        last = start + datetime.timedelta(days=399)
        for k in range(14):
            self.assertIn(f"{last - datetime.timedelta(days=k):%Y-%m-%d}", days)
        self.assertTrue(all(f.endswith("_140000.db") for f in left))
        self.assertIn("notes.txt", os.listdir(self.backups))

    def test_restore_test_mode_and_real_restore(self):
        conn = make_db(self.db_path, n_users=2)
        conn.close()
        path, _ = sauvegarde.backup(self.db_path, self.backups)
        # la base évolue après la sauvegarde
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO users(username, password_hash, role, created_at) VALUES ('tard', 'x', 'student', 'x')")
        conn.commit()
        conn.close()
        with mock.patch.object(config, "DB_PATH", self.db_path):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(restaurer.main(["--test", path]), 0)
            self.assertIn("TEST RÉUSSI", out.getvalue())
            self.assertEqual(sqlite3.connect(self.db_path).execute("SELECT count(*) FROM users").fetchone()[0], 3)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(restaurer.main([path, "--oui"]), 0)
        self.assertEqual(sqlite3.connect(self.db_path).execute("SELECT count(*) FROM users").fetchone()[0], 2)
        aside = [f for f in os.listdir(self.dir) if f.startswith("avant-restauration-")]
        self.assertEqual(len(aside), 1)  # la base remplacée est gardée de côté
        self.assertEqual(sqlite3.connect(os.path.join(self.dir, aside[0])).execute("SELECT count(*) FROM users").fetchone()[0], 3)


if __name__ == "__main__":
    unittest.main()
