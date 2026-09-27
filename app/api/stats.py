"""Statistiques pour les professeurs et administrateurs.

Niveaux : vue d'ensemble de la classe, par compétence, par chapitre, par question,
par séance, et détail d'un élève (connexions, tentatives une par une).
Filtre de période commun : ?from=AAAA-MM-JJ&to=AAAA-MM-JJ (inclus).
"""

import csv
import datetime
import io
import json
from collections import defaultdict

from .. import adaptive, db, security
from ..web import Response, json_response, router, to_int
from .assignments import progress


def _period(req):
    since, until = req.arg("from"), req.arg("to")
    if since:
        since = datetime.date.fromisoformat(since).isoformat()
    if until:
        until = (datetime.date.fromisoformat(until) + datetime.timedelta(days=1)).isoformat()
    return since, until


def _period_sql(req, col="a.answered_at"):
    since, until = _period(req)
    sql, args = "", []
    if since:
        sql += f" AND {col} >= ?"
        args.append(since)
    if until:
        sql += f" AND {col} < ?"
        args.append(until)
    return sql, args


def _class_students(conn, cid):
    return db.all_(conn, """SELECT u.id, u.username, u.display_name, u.last_login_at FROM class_members m
                            JOIN users u ON u.id = m.user_id WHERE m.class_id = ? AND u.role = 'student'
                            ORDER BY u.display_name, u.username""", cid)


def _class_access(req):
    user = security.require_staff(req)
    cid = to_int(req.params["id"])
    security.require_class_access(req.db, user, cid)
    return cid


def _in(ids):
    return ",".join("?" * len(ids)) or "NULL"


@router.get("/api/stats/classes/:id/overview")
def overview(req):
    cid = _class_access(req)
    conn = req.db
    students = _class_students(conn, cid)
    ids = [s["id"] for s in students]
    psql, pargs = _period_sql(req)
    week = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()[:19] + "Z"
    agg = {r["user_id"]: r for r in db.all_(conn, f"""
        SELECT user_id, count(*) AS answered, avg(score) AS avg_score,
               sum(CASE WHEN score >= 1 THEN 1 ELSE 0 END) AS correct,
               count(DISTINCT question_id) AS distinct_questions, max(answered_at) AS last_activity
        FROM attempts a WHERE a.score IS NOT NULL AND user_id IN ({_in(ids)}) {psql}
        GROUP BY user_id""", *ids, *pargs)}
    logins = {r["user_id"]: r for r in db.all_(conn, f"""
        SELECT user_id, count(*) AS total, sum(CASE WHEN at >= ? THEN 1 ELSE 0 END) AS week
        FROM logins WHERE user_id IN ({_in(ids)}) GROUP BY user_id""", week, *ids)}
    assigns = db.all_(conn, "SELECT id FROM assignments WHERE class_id = ? AND day <= ?", cid, db.today())
    for s in students:
        a = agg.get(s["id"], {})
        s.update({
            "answered": a.get("answered", 0), "correct": a.get("correct", 0),
            "avg_score": round(a["avg_score"], 3) if a.get("avg_score") is not None else None,
            "distinct_questions": a.get("distinct_questions", 0), "last_activity": a.get("last_activity"),
            "logins_total": logins.get(s["id"], {}).get("total", 0),
            "logins_week": logins.get(s["id"], {}).get("week", 0) or 0,
        })
        if assigns:
            progs = [progress(conn, x["id"], s["id"]) for x in assigns]
            tot = sum(p["total"] for p in progs)
            s["assignments_done"] = round(sum(p["done"] for p in progs) / tot, 3) if tot else None
            s["assignments_score"] = round(sum(p["score"] * p["total"] for p in progs) / tot, 3) if tot else None
        else:
            s["assignments_done"] = s["assignments_score"] = None
    days = db.all_(conn, f"""SELECT substr(answered_at, 1, 10) AS day, count(*) AS answered, avg(score) AS avg_score,
                                    count(DISTINCT user_id) AS students
                             FROM attempts a WHERE score IS NOT NULL AND user_id IN ({_in(ids)}) {psql}
                             GROUP BY day ORDER BY day DESC LIMIT 60""", *ids, *pargs)
    answered = [s for s in students if s["answered"]]
    summary = {
        "students": len(students),
        "active_week": sum(1 for s in students if s["logins_week"]),
        "answered": sum(s["answered"] for s in students),
        "avg_score": round(sum(s["avg_score"] * s["answered"] for s in answered) /
                           sum(s["answered"] for s in answered), 3) if answered else None,
    }
    return json_response({"summary": summary, "students": students, "days": list(reversed(days))})


def _matrix(req, cid, group_sql, names_sql, names_args):
    """Matrice élève × groupe (compétence ou chapitre) : moyenne, nombre, maîtrise pondérée."""
    conn = req.db
    students = _class_students(conn, cid)
    ids = [s["id"] for s in students]
    psql, pargs = _period_sql(req)
    groups = db.all_(conn, names_sql, *names_args)
    rows = db.all_(conn, f"""SELECT a.user_id, {group_sql} AS gid, a.score FROM attempts a
                             {"JOIN question_skills qs ON qs.question_id = a.question_id" if "qs." in group_sql
                              else "JOIN questions q ON q.id = a.question_id"}
                             WHERE a.score IS NOT NULL AND a.user_id IN ({_in(ids)}) {psql}
                             ORDER BY a.answered_at DESC, a.id DESC""", *ids, *pargs)
    scores = defaultdict(list)
    for r in rows:
        scores[(r["user_id"], r["gid"])].append(r["score"])
    cells = {}
    for (uid, gid), s in scores.items():
        cells[f"{uid}:{gid}"] = {"n": len(s), "avg": round(sum(s) / len(s), 3),
                                 "mastery": round(adaptive.weighted_mastery(s), 3)}
    for g in groups:
        all_scores = [x for (uid, gid), s in scores.items() if gid == g["id"] for x in s]
        g["n"] = len(all_scores)
        g["avg"] = round(sum(all_scores) / len(all_scores), 3) if all_scores else None
        g["students_mastered"] = sum(1 for s in students
                                     if cells.get(f"{s['id']}:{g['id']}", {}).get("mastery", 0) >= adaptive.MASTERED)
    return {"students": students, "groups": groups, "cells": cells}


@router.get("/api/stats/classes/:id/skills")
def by_skill(req):
    cid = _class_access(req)
    return json_response(_matrix(req, cid, "qs.skill_id", """
        SELECT DISTINCT s.id, s.name, c.name AS chapter FROM skills s
        JOIN question_skills qs ON qs.skill_id = s.id
        JOIN class_questions cq ON cq.question_id = qs.question_id
        LEFT JOIN chapters c ON c.id = s.chapter_id
        WHERE cq.class_id = ? ORDER BY c.position, s.name""", [cid]))


@router.get("/api/stats/classes/:id/chapters")
def by_chapter(req):
    cid = _class_access(req)
    data = _matrix(req, cid, "coalesce(q.chapter_id, 0)", """
        SELECT DISTINCT coalesce(c.id, 0) AS id, coalesce(c.name, 'Sans chapitre') AS name,
               coalesce(c.position, 9999) AS position
        FROM class_questions cq JOIN questions q ON q.id = cq.question_id
        LEFT JOIN chapters c ON c.id = q.chapter_id WHERE cq.class_id = ? ORDER BY 3, 2""", [cid])
    return json_response(data)


@router.get("/api/stats/classes/:id/questions")
def by_question(req):
    cid = _class_access(req)
    ids = [s["id"] for s in _class_students(req.db, cid)]
    psql, pargs = _period_sql(req)
    rows = db.all_(req.db, f"""
        SELECT q.id, q.uid, q.title, c.name AS chapter,
               count(a.score) AS answered, count(DISTINCT CASE WHEN a.score IS NOT NULL THEN a.user_id END) AS students,
               avg(a.score) AS avg_score, sum(CASE WHEN a.score >= 1 THEN 1 ELSE 0 END) AS correct,
               sum(CASE WHEN a.id IS NOT NULL AND a.score IS NULL THEN 1 ELSE 0 END) AS unanswered
        FROM class_questions cq JOIN questions q ON q.id = cq.question_id
        LEFT JOIN chapters c ON c.id = q.chapter_id
        LEFT JOIN attempts a ON a.question_id = q.id AND a.user_id IN ({_in(ids)}) {psql.replace('a.answered_at', 'a.created_at')}
        WHERE cq.class_id = ? GROUP BY q.id ORDER BY c.position, q.title""", *ids, *pargs, cid)
    for r in rows:
        r["avg_score"] = round(r["avg_score"], 3) if r["avg_score"] is not None else None
    return json_response({"questions": rows})


@router.get("/api/stats/classes/:id/assignments")
def by_assignment(req):
    cid = _class_access(req)
    students = _class_students(req.db, cid)
    assigns = db.all_(req.db, "SELECT id, title, day FROM assignments WHERE class_id = ? ORDER BY day DESC, id DESC",
                      cid)
    cells = {}
    for a in assigns:
        for s in students:
            p = progress(req.db, a["id"], s["id"])
            cells[f"{s['id']}:{a['id']}"] = {k: p[k] for k in ("total", "done", "mastered", "score")}
    return json_response({"students": students, "assignments": assigns, "cells": cells})


@router.get("/api/stats/students/:id")
def student_detail(req):
    user = security.require_staff(req)
    sid = to_int(req.params["id"])
    security.require_student_visibility(req.db, user, sid)
    conn = req.db
    profile = db.one(conn, "SELECT id, username, display_name, role, created_at, last_login_at FROM users WHERE id = ?",
                     sid)
    profile["classes"] = db.all_(conn, """SELECT c.id, c.name FROM classes c JOIN class_members m ON m.class_id = c.id
                                          WHERE m.user_id = ?""", sid)
    logins = db.all_(conn, "SELECT at, ip FROM logins WHERE user_id = ? ORDER BY at DESC LIMIT 100", sid)
    psql, pargs = _period_sql(req, "a.created_at")
    attempts = db.all_(conn, f"""
        SELECT a.id, a.question_id, q.uid, q.title, c.name AS chapter, a.mode, a.score, a.tries, a.created_at, a.answered_at,
               s.title AS assignment
        FROM attempts a JOIN questions q ON q.id = a.question_id LEFT JOIN chapters c ON c.id = q.chapter_id
        LEFT JOIN assignments s ON s.id = a.assignment_id
        WHERE a.user_id = ? {psql} ORDER BY a.created_at DESC LIMIT ?""", sid, *pargs,
        min(req.int_arg("limit", 300), 2000))
    mastery = adaptive.skill_mastery(conn, [sid], *_period(req)).get(sid, {})
    names = {r["id"]: r for r in db.all_(conn, """SELECT s.id, s.name, c.name AS chapter FROM skills s
                                                  LEFT JOIN chapters c ON c.id = s.chapter_id""")}
    skills = sorted(({"id": k, "name": names.get(k, {}).get("name", "?"), "chapter": names.get(k, {}).get("chapter"), **v}
                     for k, v in mastery.items()), key=lambda s: s["mastery"])
    psql2, pargs2 = _period_sql(req)
    chapters = db.all_(conn, f"""
        SELECT coalesce(c.name, 'Sans chapitre') AS name, count(*) AS n, avg(a.score) AS avg,
               count(DISTINCT a.question_id) AS questions
        FROM attempts a JOIN questions q ON q.id = a.question_id LEFT JOIN chapters c ON c.id = q.chapter_id
        WHERE a.user_id = ? AND a.score IS NOT NULL {psql2} GROUP BY c.id ORDER BY c.position""", sid, *pargs2)
    for ch in chapters:
        ch["avg"] = round(ch["avg"], 3)
    return json_response({"profile": profile, "logins": logins, "attempts": attempts, "skills": skills,
                          "chapters": chapters})


@router.get("/api/stats/classes/:id/export.csv")
def export_csv(req):
    cid = _class_access(req)
    ids = [s["id"] for s in _class_students(req.db, cid)]
    psql, pargs = _period_sql(req, "a.created_at")
    rows = db.all_(req.db, f"""
        SELECT u.username, u.display_name, q.id AS question_id, q.title, c.name AS chapter,
               (SELECT group_concat(s.name, ' | ') FROM question_skills qs JOIN skills s ON s.id = qs.skill_id
                WHERE qs.question_id = q.id) AS skills,
               a.mode, s2.title AS assignment, a.created_at, a.answered_at, a.tries, a.score, a.answers
        FROM attempts a JOIN users u ON u.id = a.user_id JOIN questions q ON q.id = a.question_id
        LEFT JOIN chapters c ON c.id = q.chapter_id LEFT JOIN assignments s2 ON s2.id = a.assignment_id
        WHERE a.user_id IN ({_in(ids)}) {psql} ORDER BY a.created_at""", *ids, *pargs)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["identifiant", "nom", "question_id", "question", "chapitre", "competences", "mode", "seance",
                "servie_le", "terminee_le", "essais", "score", "reponses"])
    for r in rows:
        answers = json.loads(r["answers"]) if r["answers"] else None
        w.writerow([r["username"], r["display_name"], r["question_id"], r["title"], r["chapter"] or "",
                    r["skills"] or "", r["mode"], r["assignment"] or "", r["created_at"], r["answered_at"] or "", r["tries"] or 0,
                    "" if r["score"] is None else str(r["score"]).replace(".", ","),
                    json.dumps(answers, ensure_ascii=False) if answers is not None else ""])
    return Response("﻿" + buf.getvalue(), content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="classe-{cid}-tentatives.csv"'})
