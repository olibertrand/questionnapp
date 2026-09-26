import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import core  # noqa: E402

OUTPUT_TEMPLATE = {
    "code": "L = randlist(4, 1, 20)\nsrc = f'print(sum({L}))'",
    "statement": "Qu'affiche `{{ src }}` ?",
    "fields": [{"type": "number", "answer": "sum(L)"}],
}

FUNC_TEMPLATE = {
    "code": "k = randint(2, 5)\ncases = [((randlist(randint(0, 6), -9, 9),), None) for _ in range(5)]\n"
            "cases = [((l,), [x * k for x in l]) for (l,), _ in cases]",
    "statement": "Écrire `mult(L)` qui multiplie chaque élément par {{ k }}.",
    "fields": [{"type": "code", "function": "mult", "cases": "cases", "forbid": ["map"]}],
}

SQL_TEMPLATE = {
    "code": "rows = [(i, choice(PRENOMS), randint(8, 20)) for i in range(1, 9)]\n"
            "seuil = randint(10, 15)\n"
            "setup = 'CREATE TABLE eleve(id INTEGER PRIMARY KEY, nom TEXT, note INTEGER);\\n' + sql_insert('eleve', rows)",
    "statement": "Noms des élèves ayant au moins {{ seuil }}.\n\n{{ sql_table(setup, 'eleve') }}",
    "fields": [{"type": "sql", "setup": "setup", "answer": "f'SELECT nom FROM eleve WHERE note >= {seuil}'"}],
}


class EngineTest(unittest.TestCase):
    def test_deterministic_and_varied(self):
        a = core.generate(OUTPUT_TEMPLATE, 1)
        b = core.generate(OUTPUT_TEMPLATE, 1)
        c = core.generate(OUTPUT_TEMPLATE, 2)
        self.assertEqual(a["public"], b["public"])
        self.assertNotEqual(a["public"], c["public"])

    def test_avoid_seen_instances(self):
        a = core.generate(OUTPUT_TEMPLATE, 7)
        b = core.generate(OUTPUT_TEMPLATE, 7, avoid=[a["fingerprint"]])
        self.assertNotEqual(a["fingerprint"], b["fingerprint"])
        self.assertTrue(b["fresh"])

    def test_number_check(self):
        inst = core.generate(OUTPUT_TEMPLATE, 3)
        total = core._build(OUTPUT_TEMPLATE, inst["seed"])[2]["L"]
        self.assertTrue(core.check(OUTPUT_TEMPLATE, 3, [str(sum(total))])["correct"])
        self.assertFalse(core.check(OUTPUT_TEMPLATE, 3, [str(sum(total) + 1)])["correct"])
        self.assertFalse(core.check(OUTPUT_TEMPLATE, 3, ["abc"])["correct"])

    def test_parse_number(self):
        self.assertEqual(core.parse_number("3,5"), 3.5)
        self.assertEqual(core.parse_number(" 1 000 "), 1000)
        self.assertEqual(core.parse_number("3/4"), 0.75)
        self.assertIsNone(core.parse_number("2+2"))

    def test_code_field(self):
        good = "def mult(L):\n    return [x * K for x in L]\n"
        ns = core._build(FUNC_TEMPLATE, 5)[2]
        res = core.check(FUNC_TEMPLATE, 5, [good.replace("K", str(ns["k"]))])
        self.assertTrue(res["correct"], res)
        res = core.check(FUNC_TEMPLATE, 5, ["def mult(L):\n    return L\n"])
        self.assertFalse(res["correct"])
        res = core.check(FUNC_TEMPLATE, 5, ["def mult(L):\n    return list(map(lambda x: x, L))\n"])
        self.assertIn("interdite", res["fields"][0]["feedback"])

    def test_code_cheating_eq_and_infinite_loop(self):
        cheat = "class A:\n    def __eq__(self, o): return True\ndef mult(L):\n    return A()\n"
        self.assertFalse(core.check(FUNC_TEMPLATE, 5, [cheat])["correct"])
        loop = "def mult(L):\n    while True: pass\n"
        res = core.check(FUNC_TEMPLATE, 5, [loop])
        self.assertFalse(res["correct"])
        self.assertIn("lent", res["fields"][0]["feedback"])
        self.assertFalse(core.check(FUNC_TEMPLATE, 5, ["import sys\nsys.exit()"])["correct"])

    def test_sql_field(self):
        ns = core._build(SQL_TEMPLATE, 9)[2]
        q = f"SELECT nom FROM eleve WHERE note >= {ns['seuil']}"
        self.assertTrue(core.check(SQL_TEMPLATE, 9, [q])["correct"])
        res = core.check(SQL_TEMPLATE, 9, ["SELECT nom, note FROM eleve"])
        self.assertFalse(res["correct"])
        self.assertIn("colonnes", res["fields"][0]["feedback"])
        self.assertFalse(core.check(SQL_TEMPLATE, 9, ["SELEC nom"])["correct"])

    def test_choice_and_text(self):
        t = {
            "code": "a = randint(1, 50)",
            "statement": "{{ a }} en binaire ?",
            "fields": [
                {"type": "text", "answer": "bin(a)[2:]", "ignore_spaces": True},
                {"type": "choice", "options": [{"text": "pair", "correct": "a % 2 == 0"},
                                               {"text": "impair", "correct": "a % 2 == 1"}]},
            ],
        }
        inst = core.generate(t, 11)
        a = core._build(t, 11)[2]["a"]
        idx = inst["public"]["fields"][1]["options"].index("pair" if a % 2 == 0 else "impair")
        res = core.check(t, 11, [" " + bin(a)[2:] + " ", idx])
        self.assertTrue(res["correct"], res)
        self.assertEqual(core.check(t, 11, [bin(a)[2:], 1 - idx])["score"], 0.5)

    def test_require_and_template_errors(self):
        t = {"code": "a = randint(1, 10)\nrequire(a > 8)", "statement": "{{ a }}",
             "fields": [{"type": "number", "answer": "a"}]}
        for seed in range(20):
            self.assertIn(core.generate(t, seed)["public"]["statement"], ("9", "10"))
        bad = {"code": "x = 1\ny = 1/0", "fields": [{"type": "number", "answer": "x"}]}
        with self.assertRaises(core.TemplateError) as ctx:
            core.generate(bad, 1)
        self.assertEqual(ctx.exception.line, 2)


def run_engine(request):
    cmd = [sys.executable, "-I", "-c",
           f"import sys; sys.path.insert(0, {ROOT!r}); from engine.runner import main; main()"]
    out = subprocess.run(cmd, input=json.dumps(request), capture_output=True, text=True, timeout=30)
    return json.loads(out.stdout)


class SandboxTest(unittest.TestCase):
    def test_runner_protocol(self):
        r = run_engine({"action": "generate", "template": OUTPUT_TEMPLATE, "seed": 1})
        self.assertTrue(r["ok"], r)

    def test_forbidden_operations(self):
        attacks = [
            "import os\nos.system('echo pwned')",
            "open('/etc/passwd').read()",
            "open('x.txt', 'w').write('x')",
            "import socket",
            "import subprocess",
        ]
        for attack in attacks:
            t = {"code": attack, "fields": [{"type": "number", "answer": "1"}]}
            r = run_engine({"action": "generate", "template": t, "seed": 1})
            self.assertFalse(r["ok"], attack)

    def test_student_code_sandboxed(self):
        t = dict(FUNC_TEMPLATE)
        r = run_engine({"action": "check", "template": t, "seed": 1,
                        "answers": ["import os\nos.system('touch /tmp/pwned')\ndef mult(L): return L"]})
        self.assertTrue(r["ok"])
        self.assertFalse(r["result"]["correct"])
        self.assertRegex(r["result"]["fields"][0]["feedback"], "interdit|pas disponible")
        self.assertFalse(os.path.exists("/tmp/pwned"))

    def test_student_cannot_read_expected_answers(self):
        cheats = [
            "import sys\ndef mult(L):\n    return sys._getframe(1).f_locals['expected']\n",
            "def mult(L):\n    try:\n        1/0\n    except Exception as e:\n"
            "        return e.__traceback__.tb_frame.f_back.f_locals['expected']\n",
            "import typing\ndef mult(L):\n    typing.sys.modules['engine.core'].same_value = lambda a, b: True\n",
            "import collections\ndef mult(L):\n    getattr(collections, '_sys').modules['engine.core'].same_value = lambda a, b: True\n",
            "def mult(L):\n    return ().__class__.__base__.__subclasses__()\n",
        ]
        for cheat in cheats:
            r = run_engine({"action": "check", "template": FUNC_TEMPLATE, "seed": 3, "answers": [cheat]})
            self.assertFalse(r["result"]["correct"], cheat)

    def test_sql_attach_denied(self):
        t = {"code": "setup = 'CREATE TABLE t(a);'", "fields": [{"type": "sql", "setup": "setup", "answer": "'SELECT a FROM t'"}]}
        r = run_engine({"action": "check", "template": t, "seed": 1, "answers": ["ATTACH DATABASE 'x.db' AS x"]})
        self.assertIn("not authorized", r["result"]["fields"][0]["feedback"])


if __name__ == "__main__":
    unittest.main()
