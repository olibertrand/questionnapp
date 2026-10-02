#!/usr/bin/env python3
"""Remplit la base avec des données de démonstration.

  python3 scripts/demo.py            (utilise QUESTIONNAPP_DB ou data/questionnapp.db)

Crée : admin/admin (si la base est vide), prof/prof, 12 élèves eleve01..eleve12 (mot de passe « eleve »),
la classe « 1re NSI », les questions d'exemple, trois séances et deux semaines d'activité simulée.
"""

import datetime
import glob
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QUESTIONNAPP_ADMIN_PASSWORD", "admin")

from app import db, security, server  # noqa: E402
from app.api.questions import save_question  # noqa: E402
from engine import core  # noqa: E402

NAMES = ["Alice Martin", "Bilal Nasri", "Chloé Petit", "David Leroy", "Emma Garnier", "Farid Benali",
         "Gabriel Roux", "Hugo Lambert", "Inès Moreau", "Jade Fontaine", "Karim Haddad", "Léa Dubois"]


def iso(dt):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def wrong_answers(template, seed):
    public, priv, _ = core._build(template, seed)
    out = []
    for f, pub, prv in zip(template["fields"], public["fields"], priv["fields"]):
        t = f["type"]
        if t == "number":
            out.append(str(prv["expected"] + random.choice([-1, 1, 2])))
        elif t == "text":
            out.append(prv["accepted"][0][:-1] or "?")
        elif t == "choice":
            bad = [i for i in range(len(pub["options"])) if i not in prv["correct"]]
            out.append(random.choice(bad))
        elif t == "sql":
            out.append("SELECT * FROM " + re.findall(r"FROM (\w+)", prv["query"])[0])
        else:
            out.append("def f(L):\n    return 0\n")
    return out


def good_answers(template, seed):
    from tests.test_banque import reference_answers
    return reference_answers(template, seed)


def main():
    server.bootstrap()
    conn = db.connect()
    rng = random.Random(2026)
    random.seed(2026)
    if db.one(conn, "SELECT id FROM users WHERE username = 'prof'"):
        print("Données de démonstration déjà présentes.")
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    prof = db.insert(conn, "INSERT INTO users(username, password_hash, display_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                     "prof", security.hash_password("prof"), "M. Durand", "teacher", db.now())
    cid = db.insert(conn, "INSERT INTO classes(name, description, created_by, created_at) VALUES (?, ?, ?, ?)",
                    "1re NSI", "Spécialité NSI, groupe A", prof, db.now())
    conn.execute("INSERT INTO class_members(class_id, user_id) VALUES (?, ?)", (cid, prof))
    students = []
    for i, name in enumerate(NAMES, 1):
        uid = db.insert(conn, "INSERT INTO users(username, password_hash, display_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                        f"eleve{i:02d}", security.hash_password("eleve"), name, "student", db.now())
        conn.execute("INSERT INTO class_members(class_id, user_id) VALUES (?, ?)", (cid, uid))
        students.append((uid, rng.uniform(0.35, 0.95)))  # niveau de l'élève simulé

    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "banque", "*.json"))):
        with open(path, encoding="utf-8") as f:
            items += json.load(f)["questions"]
    user = {"id": prof, "role": "teacher"}
    qids = []
    for item in items:
        qids.append(save_question(conn, user, {
            "uid": item.get("uid"), "title": item["title"], "difficulty": item["difficulty"], "skills": item["skills"],
            "template": item["template"], "chapter_name": item["chapter"], "class_ids": [cid]}, validate=False))
    print(f"{len(qids)} questions importées")

    today = datetime.date.today()
    by_chapter = lambda ch: [q for q, it in zip(qids, items) if it["chapter"] == ch]  # noqa: E731
    plan = [("Boucles et conditions", today - datetime.timedelta(days=7), by_chapter("Python : les bases")),
            ("Listes et tris", today - datetime.timedelta(days=2),
             by_chapter("Python : listes et chaînes")[:2] + by_chapter("Algorithmique")[:2]),
            ("Dictionnaires", today - datetime.timedelta(days=1), by_chapter("Python : dictionnaires")[:6]),
            ("SQL : premières requêtes", today, by_chapter("Bases de données")[:3]),
            ("Représentation des données", today + datetime.timedelta(days=3), by_chapter("Représentation des données et architecture"))]
    assignments = []
    for title, day, aq in plan:
        aid = db.insert(conn, "INSERT INTO assignments(class_id, title, day, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                        cid, title, day.isoformat(), prof, db.now())
        for pos, qid in enumerate(aq):
            conn.execute("INSERT INTO assignment_questions(assignment_id, question_id, position) VALUES (?, ?, ?)", (aid, qid, pos))
        assignments.append((aid, day, aq))

    # un groupe et une séance thématique pour ce groupe
    gid = db.insert(conn, "INSERT INTO groups(class_id, name) VALUES (?, ?)", cid, "Soutien")
    for uid, _level in students[:4]:
        conn.execute("INSERT INTO group_members(group_id, user_id) VALUES (?, ?)", (gid, uid))
    tid = db.insert(conn, "INSERT INTO assignments(class_id, title, day, kind, created_by, created_at) VALUES (?, ?, ?, 'theme', ?, ?)",
                    cid, "Révisions : dictionnaires", today.isoformat(), prof, db.now())
    conn.execute("INSERT INTO assignment_targets(assignment_id, group_id) VALUES (?, ?)", (tid, gid))
    for pos, qid in enumerate(by_chapter("Python : dictionnaires")[6:12]):
        conn.execute("INSERT INTO assignment_questions(assignment_id, question_id, position) VALUES (?, ?, ?)", (tid, qid, pos))

    templates = {qid: json.loads(db.one(conn, """SELECT v.template FROM questions q JOIN question_versions v
                                                ON v.id = q.version_id WHERE q.id = ?""", qid)["template"]) for qid in qids}
    versions = {qid: db.one(conn, "SELECT version_id FROM questions WHERE id = ?", qid)["version_id"] for qid in qids}
    difficulty = {qid: it["difficulty"] for qid, it in zip(qids, items)}
    n_attempts = 0
    conn.execute("BEGIN")
    for uid, level in students:
        for day_offset in range(14, -1, -1):
            if rng.random() > 0.45 + level * 0.3:
                continue
            day = now - datetime.timedelta(days=day_offset, hours=rng.randint(0, 8))
            conn.execute("INSERT INTO logins(user_id, at, ip) VALUES (?, ?, ?)", (uid, iso(day), "127.0.0.1"))
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (iso(day), uid))
            todays = [a for a in assignments if a[1] <= day.date()]
            for k in range(rng.randint(2, 7)):
                if todays and rng.random() < 0.5:
                    aid, _, aq = rng.choice(todays)
                    qid, mode = rng.choice(aq), "assignment"
                else:
                    aid, qid, mode = None, rng.choice(qids), rng.choice(["adaptive", "chapter"])
                tpl = templates[qid]
                seed = rng.getrandbits(32)
                inst = core.generate(tpl, seed)
                progress_bonus = (14 - day_offset) * 0.015
                p_ok = max(0.05, min(0.97, level + progress_bonus - 0.12 * (difficulty[qid] - 1)))
                answers = good_answers(tpl, inst["seed"]) if rng.random() < p_ok else wrong_answers(tpl, inst["seed"])
                result = core.check(tpl, inst["seed"], answers)
                served = day + datetime.timedelta(minutes=k * 4)
                answered = served + datetime.timedelta(seconds=rng.randint(20, 240))
                unanswered = rng.random() < 0.05
                tries = 1
                history = None if unanswered else json.dumps([{"answers": answers, "score": result["score"], "at": iso(answered)}])
                conn.execute("""INSERT INTO attempts(user_id, question_id, version_id, assignment_id, mode, seed, fingerprint,
                                instance, answers, result, score, tries, history, created_at, answered_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (uid, qid, versions[qid], aid, mode, inst["seed"], inst["fingerprint"],
                              json.dumps(inst["public"], ensure_ascii=False),
                              None if unanswered else json.dumps(answers, ensure_ascii=False),
                              None if unanswered else json.dumps(result, ensure_ascii=False),
                              None if unanswered else result["score"], 0 if unanswered else tries, history,
                              iso(served), None if unanswered else iso(answered)))
                n_attempts += 1
    conn.execute("COMMIT")
    print(f"{len(students)} élèves, {n_attempts} réponses simulées")
    print("Comptes : admin/admin · prof/prof · eleve01..eleve12 / eleve")


if __name__ == "__main__":
    main()
