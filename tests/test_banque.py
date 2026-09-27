"""Chaque fichier du répertoire banque/ doit être valide et chaque question passer l'auto-test
du moteur (génération sur 30 tirages, variété, correction de référence acceptée, tests non triviaux)."""

import glob
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import core  # noqa: E402

BANK_FILES = sorted(glob.glob(os.path.join(ROOT, "banque", "*.json")))


def all_questions():
    for path in BANK_FILES:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for q in data["questions"]:
            yield os.path.basename(path), q


def reference_answers(template, seed):
    """Réponses parfaites d'une instance (utilisé aussi par scripts/demo.py)."""
    public, priv, _ns = core._build(template, seed)
    return core.reference_answers(template, public, priv)[0]


class BankTest(unittest.TestCase):
    def test_files_format(self):
        self.assertGreaterEqual(len(BANK_FILES), 5)
        titles, uids = [], []
        for path in BANK_FILES:
            with self.subTest(os.path.basename(path)):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data.get("format"), "questionnapp/questions")
                self.assertTrue(data.get("title"))
                for q in data["questions"]:
                    for key in ("uid", "title", "chapter", "skills", "difficulty", "template"):
                        self.assertIn(key, q, q.get("title"))
                    self.assertTrue(q["skills"], q["title"])
                    titles.append(q["title"])
                    uids.append(q["uid"])
                    self.assertRegex(q["uid"], r"^[A-Z0-9_-]{1,40}$")
        self.assertEqual(len(titles), len(set(titles)), "titres en double dans la banque")
        self.assertEqual(len(uids), len(set(uids)), "identifiants en double dans la banque")

    def test_every_question_passes_selftest(self):
        for filename, q in all_questions():
            with self.subTest(f"{filename} : {q['title']}"):
                report = core.selftest(q["template"], samples=30)
                self.assertEqual(report["status"], "ok", report)
                self.assertGreaterEqual(report["distinct"], 4)

    def test_selftest_detects_problems(self):
        bad_ref = {"code": "a = randint(1, 9)", "statement": "{{ a }}",
                   "fields": [{"type": "code", "function": "f", "cases": "[((a,), a * 2)]"}],
                   "solution": "```python\ndef f(x):\n    return x * 3\n```"}
        r = core.selftest(bad_ref, samples=5)
        self.assertEqual(r["status"], "error")
        self.assertIn("référence est refusée", r["errors"][0]["error"])

        lax = {"code": "a = randint(1, 9)", "statement": "{{ a }}",
               "fields": [{"type": "code", "tests": "check(True)"}],
               "solution": "```python\nprint(1)\n```"}
        r = core.selftest(lax, samples=3)
        self.assertTrue(any("ne fait rien" in w for w in r["warnings"]), r)

        crash = {"code": "x = 1 / randint(0, 1)", "statement": "", "fields": [{"type": "number", "answer": "x"}]}
        self.assertEqual(core.selftest(crash, samples=10)["status"], "error")

        dull = {"code": "", "statement": "2 + 2 ?", "fields": [{"type": "number", "answer": "4"}]}
        r = core.selftest(dull, samples=5)
        self.assertTrue(any("variété" in w for w in r["warnings"]))


if __name__ == "__main__":
    unittest.main()
