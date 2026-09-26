"""Chaque question d'exemple doit passer l'auto-test du moteur (génération, variété, correction)."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import core  # noqa: E402

EXAMPLES = os.path.join(ROOT, "examples", "questions-informatique.json")


def reference_answers(template, seed):
    public, priv, _ns = core._build(template, seed)
    return core.reference_answers(template, public, priv)[0]


class ExamplesTest(unittest.TestCase):
    def test_examples(self):
        with open(EXAMPLES, encoding="utf-8") as f:
            questions = json.load(f)["questions"]
        self.assertGreater(len(questions), 10)
        for q in questions:
            with self.subTest(q["title"]):
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
