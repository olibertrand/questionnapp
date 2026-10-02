"""Maîtrise des compétences et choix de la prochaine question.

Maîtrise d'une compétence pour un élève (entre 0 et 1) : moyenne pondérée des scores
des tentatives répondues sur les questions liées à cette compétence, les plus
récentes pesant le plus (poids DECAY**rang), avec un a priori de 0,5 valant
PRIOR_WEIGHT tentative. Une compétence jamais travaillée vaut donc 0,5.
"""

import random
from collections import defaultdict

from . import db

DECAY = 0.75
PRIOR = 0.5
PRIOR_WEIGHT = 1.0
MASTERED = 0.8


def available_questions(conn, user_id, chapter_id=None):
    """Questions (non archivées) accessibles à l'élève : affectées à l'une de ses classes, ou
    faisant partie d'une séance active qui lui est destinée (séance pour certains élèves)."""
    from .api.assignments import VISIBLE_SQL
    sql = f"""SELECT q.id, q.title, q.chapter_id, q.difficulty FROM questions q
              WHERE q.archived = 0 AND q.version_id IS NOT NULL
              AND (q.id IN (SELECT cq.question_id FROM class_questions cq
                            JOIN class_members m ON m.class_id = cq.class_id WHERE m.user_id = :u)
                   OR q.id IN (SELECT aq.question_id FROM assignment_questions aq
                               JOIN assignments a ON a.id = aq.assignment_id WHERE {VISIBLE_SQL}))"""
    args = {"u": user_id}
    if chapter_id is not None:
        sql += " AND q.chapter_id = :c"
        args["c"] = chapter_id
    return conn.execute(sql, args).fetchall()


def question_skills(conn, question_ids):
    out = defaultdict(list)
    if not question_ids:
        return out
    marks = ",".join("?" * len(question_ids))
    for r in db.all_(conn, f"SELECT question_id, skill_id FROM question_skills WHERE question_id IN ({marks})",
                     *question_ids):
        out[r["question_id"]].append(r["skill_id"])
    return out


def weighted_mastery(scores_newest_first):
    num, den = PRIOR * PRIOR_WEIGHT, PRIOR_WEIGHT
    w = 1.0
    for s in scores_newest_first:
        num += w * s
        den += w
        w *= DECAY
    return num / den


def skill_mastery(conn, user_ids, since=None, until=None):
    """{user_id: {skill_id: {"mastery", "attempts", "avg"}}}"""
    if not user_ids:
        return {}
    marks = ",".join("?" * len(user_ids))
    sql = f"""SELECT a.user_id, qs.skill_id, a.score FROM attempts a
              JOIN question_skills qs ON qs.question_id = a.question_id
              WHERE a.score IS NOT NULL AND a.user_id IN ({marks})"""
    args = list(user_ids)
    if since:
        sql += " AND a.answered_at >= ?"
        args.append(since)
    if until:
        sql += " AND a.answered_at < ?"
        args.append(until)
    scores = defaultdict(lambda: defaultdict(list))
    for r in db.all_(conn, sql + " ORDER BY a.answered_at DESC, a.id DESC", *args):
        scores[r["user_id"]][r["skill_id"]].append(r["score"])
    return {
        uid: {sid: {"mastery": round(weighted_mastery(s), 3), "attempts": len(s), "avg": round(sum(s) / len(s), 3)}
              for sid, s in per_skill.items()}
        for uid, per_skill in scores.items()
    }


def _history(conn, user_id):
    """Tentatives répondues de l'élève, de la plus récente à la plus ancienne."""
    return db.all_(conn, """SELECT question_id, score FROM attempts
                            WHERE user_id = ? AND score IS NOT NULL ORDER BY answered_at DESC, id DESC LIMIT 500""",
                   user_id)


def pick_adaptive(conn, user_id, chapter_id=None, rng=None):
    """Favorise les compétences les moins maîtrisées, en évitant de répéter la même question."""
    rng = rng or random.SystemRandom()
    questions = available_questions(conn, user_id, chapter_id)
    if not questions:
        return None
    qids = [q["id"] for q in questions]
    skills = question_skills(conn, qids)
    mastery = skill_mastery(conn, [user_id]).get(user_id, {})
    history = _history(conn, user_id)
    recent = [h["question_id"] for h in history[:4]]
    per_question = defaultdict(list)
    for h in history:
        per_question[h["question_id"]].append(h["score"])

    weights = []
    for q in questions:
        sk = skills.get(q["id"])
        if sk:
            need = sum(1 - mastery.get(s, {"mastery": PRIOR})["mastery"] for s in sk) / len(sk)
        else:
            need = 1 - weighted_mastery(per_question.get(q["id"], []))
        if q["id"] not in per_question:
            need += 0.25  # jamais vue : on explore
        w = (0.05 + need) ** 2
        if recent and q["id"] == recent[0]:
            w *= 0.02
        elif q["id"] in recent:
            w *= 0.3
        weights.append(w)
    return rng.choices(questions, weights=weights, k=1)[0]


def pick_chapter(conn, user_id, chapter_id, rng=None):
    """Parcourt toutes les questions du chapitre : d'abord les moins travaillées."""
    rng = rng or random.SystemRandom()
    questions = available_questions(conn, user_id, chapter_id)
    if not questions:
        return None
    counts = defaultdict(int)
    for r in db.all_(conn, """SELECT question_id, count(*) AS n FROM attempts
                              WHERE user_id = ? AND score IS NOT NULL GROUP BY question_id""", user_id):
        counts[r["question_id"]] = r["n"]
    last = db.one(conn, "SELECT question_id FROM attempts WHERE user_id = ? ORDER BY id DESC LIMIT 1", user_id)
    candidates = [q for q in questions if not last or q["id"] != last["question_id"]] or questions
    low = min(counts[q["id"]] for q in candidates)
    return rng.choice([q for q in candidates if counts[q["id"]] == low])
