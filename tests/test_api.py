"""Tests d'intégration de l'API : un vrai serveur HTTP sur un port libre, une base temporaire."""

import datetime
import http.cookiejar
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP = tempfile.mkdtemp(prefix="qa-test-")
os.environ["QUESTIONNAPP_DB"] = os.path.join(TMP, "test.db")
os.environ["QUESTIONNAPP_ADMIN_PASSWORD"] = "admin-pass"
os.environ["QUESTIONNAPP_QUIET"] = "1"

from http.server import ThreadingHTTPServer  # noqa: E402

from app import server  # noqa: E402

TEMPLATE = {
    "code": "a = randint(2, 9)\nb = randint(2, 9)",
    "statement": "Combien vaut {{ a }} × {{ b }} ?",
    "fields": [{"type": "number", "answer": "a * b"}],
    "solution": "{{ a * b }}",
}


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None, csrf=True):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if csrf:
            req.add_header("X-Requested-With", "questionnapp")
        try:
            with self.opener.open(req) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")

    def ok(self, method, path, body=None):
        status, data = self.call(method, path, body)
        assert status < 400, (method, path, status, data)
        return data

    def login(self, username, password):
        return self.ok("POST", "/api/auth/login", {"username": username, "password": password})


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.bootstrap()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_full_scenario(self):
        admin = Client(self.base)
        self.assertEqual(admin.call("POST", "/api/auth/login", {"username": "admin", "password": "bad"})[0], 401)
        admin.login("admin", "admin-pass")
        # CSRF : mutation sans en-tête refusée
        self.assertEqual(admin.call("POST", "/api/classes", {"name": "X"}, csrf=False)[0], 403)

        admin.ok("POST", "/api/users", {"username": "prof1", "password": "prof", "display_name": "Prof", "role": "teacher"})
        prof = Client(self.base)
        prof.login("prof1", "prof")
        cid = prof.ok("POST", "/api/classes", {"name": "NSI"})["id"]
        other_cid = admin.ok("POST", "/api/classes", {"name": "Autre"})["id"]
        # un prof ne gère pas une classe dont il n'est pas membre
        self.assertEqual(prof.call("GET", f"/api/classes/{other_cid}")[0], 403)
        # un prof ne crée pas d'admin
        self.assertEqual(prof.call("POST", "/api/users", {"username": "x", "password": "xxxx", "role": "admin"})[0], 403)

        r = prof.ok("POST", "/api/users/import", {"csv": "e1;pass1;Élève Un\ne2;pass2;Élève Deux\nmauvaise ligne", "class_id": cid})
        self.assertEqual(r["created"], ["e1", "e2"])
        self.assertEqual(len(r["errors"]), 1)

        # modèle invalide refusé avec le numéro de ligne
        status, err = prof.call("POST", "/api/questions", {"title": "Bug", "template": {
            "code": "a = 1\nb = a / 0", "fields": [{"type": "number", "answer": "a"}]}})
        self.assertEqual(status, 422)
        self.assertEqual(err["line"], 2)

        qid = prof.ok("POST", "/api/questions", {"title": "Tables", "chapter_name": "Calcul", "skills": ["Multiplier"],
                                                 "template": TEMPLATE, "class_ids": [cid]})["id"]
        q = prof.ok("GET", f"/api/questions/{qid}")["question"]
        self.assertEqual(q["class_ids"], [cid])
        self.assertEqual(q["skills"], ["Multiplier"])
        prev = prof.ok("POST", "/api/questions/preview", {"template": TEMPLATE, "seed": 5})
        self.assertTrue(prev["ok"])
        self.assertGreater(prev["result"]["variety"]["distinct"], 5)

        aid = prof.ok("POST", "/api/assignments", {"class_id": cid, "title": "Séance 1", "day": datetime.date.today().isoformat(),
                                                   "question_ids": [qid]})["ids"][0]

        eleve = Client(self.base)
        eleve.login("e1", "pass1")
        self.assertEqual(eleve.call("GET", "/api/questions")[0], 403)
        dash = eleve.ok("GET", "/api/me/dashboard")
        self.assertEqual(len(dash["assignments"]), 1)
        self.assertEqual(dash["chapters"][0]["questions"], 1)

        seen = set()
        for _ in range(3):
            at = eleve.ok("POST", "/api/practice/next", {"mode": "assignment", "assignment_id": aid, "question_id": qid})["attempt"]
            self.assertNotIn(at["instance"]["statement"], seen, "même énoncé servi deux fois")
            seen.add(at["instance"]["statement"])
            self.assertNotIn("answer", json.dumps(at))  # la réponse n'est jamais envoyée à l'élève
        nums = [int(x) for x in at["instance"]["statement"].split() if x.isdigit()]
        res = eleve.ok("POST", f"/api/attempts/{at['id']}/answer", {"answers": [str(nums[0] * nums[1])]})
        self.assertTrue(res["result"]["correct"])
        self.assertEqual(res["progress"]["mastered"], 1)
        self.assertEqual(eleve.call("POST", f"/api/attempts/{at['id']}/answer", {"answers": ["0"]})[0], 409)

        for mode in ("adaptive", "chapter"):
            body = {"mode": mode}
            if mode == "chapter":
                body["chapter_id"] = q["chapter_id"]
            at2 = eleve.ok("POST", "/api/practice/next", body)["attempt"]
            eleve.ok("POST", f"/api/attempts/{at2['id']}/answer", {"answers": ["-1"]})

        # un autre élève ne peut pas répondre à la place du premier
        e2 = Client(self.base)
        e2.login("e2", "pass2")
        self.assertEqual(e2.call("POST", f"/api/attempts/{at2['id']}/answer", {"answers": ["1"]})[0], 403)
        self.assertEqual(e2.call("GET", f"/api/attempts/{at['id']}")[0], 403)

        ov = prof.ok("GET", f"/api/stats/classes/{cid}/overview")
        s1 = next(s for s in ov["students"] if s["username"] == "e1")
        self.assertEqual(s1["answered"], 3)
        self.assertEqual(s1["logins_total"], 1)
        sk = prof.ok("GET", f"/api/stats/classes/{cid}/skills")
        self.assertEqual(len(sk["groups"]), 1)
        detail = prof.ok("GET", f"/api/stats/students/{s1['id']}")
        self.assertEqual(len(detail["attempts"]), 5)
        prof.ok("GET", f"/api/stats/classes/{cid}/chapters")
        prof.ok("GET", f"/api/stats/classes/{cid}/questions")
        prof.ok("GET", f"/api/stats/classes/{cid}/assignments")
        prof.ok("GET", f"/api/attempts/{at['id']}")
        self.assertEqual(prof.call("GET", f"/api/stats/classes/{other_cid}/overview")[0], 403)

        # nouvelle version du modèle : les anciennes tentatives restent consultables
        tpl2 = dict(TEMPLATE, statement="Calculer {{ a }} fois {{ b }}.")
        prof.ok("PUT", f"/api/questions/{qid}", {"title": "Tables", "template": tpl2})
        self.assertIn("×", prof.ok("GET", f"/api/attempts/{at['id']}")["attempt"]["instance"]["statement"])
        # suppression d'une question déjà utilisée = archivage
        self.assertTrue(prof.ok("DELETE", f"/api/questions/{qid}")["archived"])

        # banque d'exemples : import en un clic, sans doublon au second appel
        examples = prof.ok("GET", "/api/questions/examples")["questions"]
        self.assertFalse(any(e["imported"] for e in examples))
        one = prof.ok("POST", "/api/questions/import-examples", {"titles": [examples[0]["title"]]})
        self.assertEqual(len(one["created"]), 1)
        self.assertTrue(prof.ok("GET", "/api/questions/examples")["questions"][0]["imported"])
        ex = prof.ok("POST", "/api/questions/import-examples", {"class_ids": [cid]})
        self.assertEqual(len(ex["created"]), len(examples) - 1)
        self.assertEqual(prof.ok("POST", "/api/questions/import-examples", {})["created"], [])
        self.assertEqual(eleve.call("POST", "/api/questions/import-examples", {})[0], 403)
        self.assertGreater(len(eleve.ok("GET", "/api/me/dashboard")["chapters"]), 3)

        # import d'un fichier (ex. produit par Claude) : auto-test de chaque question
        bundle = {"format": "questionnapp/questions", "version": 1, "questions": [
            {"title": "Dico : accès", "chapter": "Dictionnaires", "skills": ["Dictionnaires : accès"],
             "template": {"code": "k = choice(['a', 'b'])\nv = randint(1, 50)", "statement": "d = {'{{ k }}': {{ v }}} ; d['{{ k }}'] ?",
                          "fields": [{"type": "number", "answer": "v"}]}},
            {"title": "Plante", "template": {"code": "x = 1 / 0", "fields": [{"type": "number", "answer": "1"}]}},
            {"title": "Correction fausse", "chapter": "Dictionnaires", "template": {
                "code": "n = randint(1, 9)", "statement": "Écrire double(x) ({{ n }})",
                "fields": [{"type": "code", "function": "double", "cases": "[((n,), 2 * n)]"}],
                "solution": "```python\ndef double(x):\n    return x + 1\n```"}},
        ]}
        r = prof.ok("POST", "/api/questions/import", bundle)
        self.assertEqual(len(r["created"]), 2)
        self.assertEqual(len(r["errors"]), 1)
        self.assertEqual([w["title"] for w in r["warnings"]], ["Correction fausse"])
        st = prof.ok("POST", "/api/questions/selftest", {"template": bundle["questions"][0]["template"]})
        self.assertEqual(st["status"], "ok")
        req = urllib.request.Request(self.base + "/api/questions/referential")
        with prof.opener.open(req) as resp:
            ref = resp.read().decode()
        self.assertIn("## Chapitre : Dictionnaires", ref)
        self.assertIn("Dictionnaires : accès", ref)

        eleve.ok("POST", "/api/auth/logout")
        self.assertEqual(eleve.call("GET", "/api/me/dashboard")[0], 401)


if __name__ == "__main__":
    unittest.main()
