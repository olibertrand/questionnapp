"""Chaque question d'exemple doit se générer sans erreur, varier, et accepter sa propre réponse."""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import core  # noqa: E402

EXAMPLES = os.path.join(ROOT, "examples", "questions-informatique.json")


def reference_answers(template, seed):
    public, priv, _ns = core._build(template, seed)
    answers = []
    for f, pub, prv in zip(template["fields"], public["fields"], priv["fields"]):
        t = f["type"]
        if t == "number":
            answers.append(str(prv["expected"]).replace(".", ","))
        elif t == "text":
            answers.append(prv["accepted"][0])
        elif t == "choice":
            answers.append(prv["correct"] if f.get("multiple") else prv["correct"][0])
        elif t == "sql":
            answers.append(prv["query"])
        elif t == "code":
            m = re.search(r"```python\n(.*?)```", priv["solution"], re.S)
            answers.append(m.group(1) if m else "")
    return answers


class ExamplesTest(unittest.TestCase):
    def test_examples(self):
        with open(EXAMPLES, encoding="utf-8") as f:
            questions = json.load(f)["questions"]
        self.assertGreater(len(questions), 10)
        for q in questions:
            with self.subTest(q["title"]):
                fps = set()
                for seed in range(30):
                    inst = core.generate(q["template"], seed)
                    fps.add(inst["fingerprint"])
                    res = core.check(q["template"], seed, reference_answers(q["template"], seed))
                    self.assertTrue(res["correct"], (seed, res))
                self.assertGreaterEqual(len(fps), 4, "pas assez de variété")


if __name__ == "__main__":
    unittest.main()
