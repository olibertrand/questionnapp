"""Vérifie l'interface : syntaxe des modules JavaScript (si Node.js est installé) et absence
de toute ressource chargée depuis un serveur extérieur (RGPD et sécurité)."""

import glob
import os
import re
import sys
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(shutil.which("node"), "Node.js non installé")
class WebSyntaxTest(unittest.TestCase):
    def test_js_syntax(self):
        files = glob.glob(os.path.join(ROOT, "web", "js", "**", "*.js"), recursive=True)
        self.assertTrue(files)
        for path in files:
            with self.subTest(os.path.relpath(path, ROOT)):
                r = subprocess.run(["node", "--experimental-default-type=module", "--check", path],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)


class NoExternalResourceTest(unittest.TestCase):
    """Le navigateur ne doit contacter que l'appli : ni police, ni script, ni feuille de style extérieurs."""

    def test_csp_self_only(self):
        sys.path.insert(0, ROOT)
        from app.server import SECURITY_HEADERS
        csp = SECURITY_HEADERS["Content-Security-Policy"]
        self.assertNotRegex(csp, r"https?://", csp)

    def test_no_external_url_in_interface(self):
        files = [os.path.join(ROOT, "web", "index.html")]
        files += glob.glob(os.path.join(ROOT, "web", "js", "**", "*.js"), recursive=True)
        files += glob.glob(os.path.join(ROOT, "web", "css", "*.css"))
        for path in files:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            # seul l'espace de noms SVG (un identifiant, jamais téléchargé) est permis
            urls = [u for u in re.findall(r"https?://[^\s\"'()<>]+", text) if not u.startswith("http://www.w3.org/")]
            with self.subTest(os.path.relpath(path, ROOT)):
                self.assertEqual(urls, [])

    def test_vendored_highlight_present(self):
        for name in ("highlight.min.js", "github.min.css", "github-dark.min.css", "LICENSE"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "web", "vendor", "highlight", name)), name)


if __name__ == "__main__":
    unittest.main()
