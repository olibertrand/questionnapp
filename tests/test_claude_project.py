"""Les fichiers du projet Claude doivent être à jour et le moteur autonome utilisable."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ClaudeProjectTest(unittest.TestCase):
    def test_generated_files_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_claude_project.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_standalone_engine(self):
        bad = {"questions": [
            {"title": "ok", "template": {"code": "a = randint(1, 99)", "statement": "{{ a }} ?",
                                         "fields": [{"type": "number", "answer": "a"}]}},
            {"title": "plante", "template": {"code": "a = [1][randint(0, 3)]", "fields": [{"type": "number", "answer": "a"}]}},
        ]}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "q.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bad, f)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "claude-projet", "questionnapp_moteur.py"), path],
                               capture_output=True, text=True, cwd=d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("[OK   ] 1. ok", r.stdout)
        self.assertIn("[ERREUR] 2. plante", r.stdout)
        self.assertIn("IndexError", r.stdout)


if __name__ == "__main__":
    unittest.main()
