"""Vérifie la syntaxe des modules JavaScript de l'interface (si Node.js est installé)."""

import glob
import os
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


if __name__ == "__main__":
    unittest.main()
