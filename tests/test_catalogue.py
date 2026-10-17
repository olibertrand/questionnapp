"""Le catalogue HTML des questions (scripts/catalogue.py) : toutes les questions de la banque,
un exemple chacune, une page autonome qui ne charge rien depuis l'extérieur."""

import glob
import json
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import catalogue  # noqa: E402


class CatalogueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banks = catalogue.collect(os.path.join(ROOT, "banque"), 1)
        cls.html = catalogue.build_html(cls.banks, 1)

    def test_every_question_has_an_example(self):
        uids = [q["uid"] for b in self.banks for q in b["questions"]]
        expected = []
        for path in sorted(glob.glob(os.path.join(ROOT, "banque", "*.json"))):
            with open(path, encoding="utf-8") as f:
                expected += [q["uid"] for q in json.load(f)["questions"]]
        self.assertEqual(uids, expected)
        for b in self.banks:
            for q in b["questions"]:
                self.assertNotIn("error", q, q["uid"])
                self.assertTrue(q["example"]["statement"], q["uid"])

    def test_examples_are_stable(self):
        again = catalogue.collect(os.path.join(ROOT, "banque"), 1)
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.banks, sort_keys=True))
        other = catalogue.collect(os.path.join(ROOT, "banque"), 2)
        self.assertNotEqual(json.dumps(other, sort_keys=True), json.dumps(self.banks, sort_keys=True))

    def test_self_contained_page(self):
        # aucune ressource externe : ni script, ni feuille de style, ni police chargés depuis un serveur
        self.assertIsNone(re.search(r"""<(script|link|img)[^>]+(src|href)\s*=\s*["']?(https?:)?//""", self.html, re.I))
        css = self.html.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertNotIn("@import", css)
        self.assertNotRegex(css, r"url\(\s*['\"]?(https?:)?//")
        # les données ne peuvent pas fermer la balise <script> qui les contient
        data = self.html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(len(json.loads(data)["banks"]), len(self.banks))
        self.assertIn("function renderMarkdown", self.html)
        self.assertNotRegex(self.html, r"^\s*(import|export) ", "le module markdown.js doit être mis à plat")

    def test_script_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "c.html")
            self.assertEqual(catalogue.main(["--sortie", out]), 0)
            with open(out, encoding="utf-8") as f:
                self.assertIn("<title>Catalogue des questions</title>", f.read())


if __name__ == "__main__":
    unittest.main()
