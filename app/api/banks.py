"""Banques de questions : fichiers JSON du répertoire banque/ (un par thème).

Le répertoire est une bibliothèque partageable et versionnée ; la base de données reste la
version de travail (questions affectées aux classes, versions, statistiques). On importe
depuis un fichier les questions nouvelles, et on met à jour celles qui y ont été modifiées.
"""

import json
import os
import re

from .. import config, db, security
from ..web import HttpError, int_list, json_response, router
from .questions import _import_items, _selftest_messages, save_question, selftest

_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _path(bank_id):
    if not _ID.match(bank_id or ""):
        raise HttpError(404, "Banque introuvable")
    path = os.path.join(config.BANK_DIR, bank_id + ".json")
    if not os.path.isfile(path):
        raise HttpError(404, "Banque introuvable")
    return path


def load_bank(bank_id):
    with open(_path(bank_id), encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(questions, list):
        raise ValueError("liste « questions » absente")
    return {"id": bank_id, "title": (data.get("title") if isinstance(data, dict) else None) or bank_id,
            "description": data.get("description", "") if isinstance(data, dict) else "",
            "questions": [q for q in questions if isinstance(q, dict) and q.get("title")]}


def bank_ids():
    if not os.path.isdir(config.BANK_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(config.BANK_DIR) if f.endswith(".json") and _ID.match(f[:-5]))


def _current(conn):
    """Questions non archivées par titre : {titre: (id, modèle)}."""
    rows = db.all_(conn, """SELECT q.id, q.title, v.template FROM questions q
                            JOIN question_versions v ON v.id = q.version_id WHERE q.archived = 0""")
    return {r["title"]: (r["id"], json.loads(r["template"])) for r in rows}


def _status(item, current):
    if item["title"] not in current:
        return "new", None
    qid, template = current[item["title"]]
    return ("imported" if template == item.get("template") else "modified"), qid


@router.get("/api/banks")
def list_banks(req):
    security.require_staff(req)
    current = _current(req.db)
    banks = []
    for bid in bank_ids():
        try:
            b = load_bank(bid)
        except (ValueError, OSError) as exc:
            banks.append({"id": bid, "title": bid, "error": f"fichier illisible : {exc}"})
            continue
        counts = {"new": 0, "imported": 0, "modified": 0}
        for item in b["questions"]:
            counts[_status(item, current)[0]] += 1
        banks.append({"id": bid, "title": b["title"], "description": b["description"],
                      "count": len(b["questions"]), **counts})
    return json_response({"dir": config.BANK_DIR, "banks": banks})


@router.get("/api/banks/:id")
def get_bank(req):
    security.require_staff(req)
    try:
        b = load_bank(req.params["id"])
    except ValueError as exc:
        raise HttpError(422, f"Fichier illisible : {exc}") from None
    current = _current(req.db)
    for item in b["questions"]:
        item["status"], item["question_id"] = _status(item, current)
    return json_response({"bank": b})


@router.post("/api/banks/:id/import")
def import_bank(req):
    """Importe les questions `titles` (nouvelles) et met à jour les questions `update`
    (déjà importées mais modifiées dans le fichier : nouvelle version, réponses passées conservées)."""
    user = security.require_staff(req)
    b = load_bank(req.params["id"])
    data = req.json
    class_ids = int_list(data, "class_ids") if "class_ids" in data else []
    for cid in class_ids:
        security.require_class_access(req.db, user, cid)
    wanted = set(data.get("titles") or [])
    to_update = set(data.get("update") or [])
    items = [q for q in b["questions"] if q["title"] in wanted]
    result = _import_items(req.db, user, items, class_ids, validate=True, skip_existing=True)

    current = _current(req.db)
    updated = []
    for item in b["questions"]:
        if item["title"] not in to_update or item["title"] not in current:
            continue
        qid, template = current[item["title"]]
        if template == item.get("template"):
            continue
        try:
            report = selftest(item.get("template") or {})
            if [e for e in report["errors"] if "référence" not in e["error"]] or not report["samples"]:
                raise HttpError(422, "; ".join(_selftest_messages(report)[:3]))
            payload = {"title": item["title"], "difficulty": item.get("difficulty", 2), "skills": item.get("skills") or [],
                       "template": item["template"], "chapter_name": item.get("chapter") or None}
            save_question(req.db, user, payload, qid, validate=False)
            for cid in class_ids:
                req.db.execute("INSERT OR IGNORE INTO class_questions(class_id, question_id) VALUES (?, ?)", (cid, qid))
            updated.append(qid)
            if report["status"] != "ok":
                result["warnings"].append({"id": qid, "title": item["title"], "messages": _selftest_messages(report)})
        except HttpError as exc:
            result["errors"].append(f"mise à jour de « {item['title']} » : {exc.message}")
    result["updated"] = updated
    return json_response(result)
