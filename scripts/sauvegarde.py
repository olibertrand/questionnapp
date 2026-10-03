#!/usr/bin/env python3
"""Sauvegarde de la base de données de QuestionnApp.

  python3 scripts/sauvegarde.py                      (sauvegarde + rotation)
  python3 scripts/sauvegarde.py --dossier /chemin    (autre dossier de sauvegarde)

- La copie est sûre même pendant que l'application tourne (API de sauvegarde de SQLite,
  et non une simple copie de fichier).
- Chaque copie est vérifiée (contrôle d'intégrité) avant d'être gardée.
- Rotation : on garde la dernière copie de chacun des 14 derniers jours et de chacun des
  12 derniers mois (réglable avec --jours et --mois) ; seules les copies plus anciennes,
  reconnues à leur nom (questionnapp-AAAA-MM-JJ_HHMMSS.db), sont supprimées.
- Code de sortie différent de 0 en cas d'échec (cron peut alors prévenir par courriel).

Dossier par défaut : variable QUESTIONNAPP_BACKUP_DIR, sinon data/sauvegardes/ à côté de la
base. Voir docs/SAUVEGARDE.md pour la planification automatique et la restauration.
"""

import argparse
import datetime
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config  # noqa: E402

NAME_RE = re.compile(r"^questionnapp-(\d{4})-(\d{2})-(\d{2})_(\d{6})\.db$")


def default_dir():
    return os.environ.get("QUESTIONNAPP_BACKUP_DIR") or os.path.join(os.path.dirname(os.path.abspath(config.DB_PATH)),
                                                                     "sauvegardes")


def summary(path):
    """Contrôle d'intégrité et quelques chiffres ; lève une exception si la copie est abîmée."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        status = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if status != "ok":
            raise RuntimeError(f"contrôle d'intégrité en échec : {status}")
        counts = {}
        for table in ("users", "questions", "attempts"):
            try:
                counts[table] = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            except sqlite3.Error:
                counts[table] = None
        return counts
    finally:
        conn.close()


def backup(db_path, dest_dir, now=None):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"base introuvable : {db_path}")
    os.makedirs(dest_dir, exist_ok=True)
    now = now or datetime.datetime.now()
    final = os.path.join(dest_dir, f"questionnapp-{now:%Y-%m-%d_%H%M%S}.db")
    tmp = final + ".partiel"
    src = sqlite3.connect(db_path, timeout=30)  # lecture seule en pratique : backup() ne modifie pas la source
    dst = sqlite3.connect(tmp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    try:
        counts = summary(tmp)
    except Exception:
        os.remove(tmp)
        raise
    os.replace(tmp, final)
    return final, counts


def rotate(dest_dir, keep_days=14, keep_months=12, protect=()):
    """Supprime les copies au-delà de la rotation ; renvoie la liste des fichiers supprimés."""
    files = []
    for name in os.listdir(dest_dir):
        m = NAME_RE.match(name)
        if m:
            files.append((name, f"{m[1]}-{m[2]}-{m[3]}", f"{m[1]}-{m[2]}"))
    files.sort(reverse=True)  # du plus récent au plus ancien (le nom contient la date et l'heure)
    keep = set(os.path.basename(p) for p in protect)
    latest_by_day, latest_by_month = {}, {}
    for name, day, month in files:
        latest_by_day.setdefault(day, name)
        latest_by_month.setdefault(month, name)
    keep.update(latest_by_day[d] for d in sorted(latest_by_day, reverse=True)[:keep_days])
    keep.update(latest_by_month[m] for m in sorted(latest_by_month, reverse=True)[:keep_months])
    removed = []
    for name, _day, _month in files:
        if name not in keep:
            os.remove(os.path.join(dest_dir, name))
            removed.append(name)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sauvegarde de la base de QuestionnApp")
    parser.add_argument("--dossier", default=None, help="dossier des sauvegardes")
    parser.add_argument("--jours", type=int, default=14, help="nombre de jours gardés (une copie par jour)")
    parser.add_argument("--mois", type=int, default=12, help="nombre de mois gardés (une copie par mois)")
    args = parser.parse_args(argv)
    dest = args.dossier or default_dir()
    stamp = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    try:
        path, counts = backup(config.DB_PATH, dest)
        removed = rotate(dest, args.jours, args.mois, protect=[path])
    except Exception as exc:  # noqa: BLE001
        print(f"[{stamp}] ÉCHEC de la sauvegarde de {config.DB_PATH} : {exc}", file=sys.stderr)
        return 1
    size = os.path.getsize(path) / 1024
    print(f"[{stamp}] sauvegarde OK : {path} ({size:.0f} Ko ; {counts['users']} comptes, "
          f"{counts['questions']} questions, {counts['attempts']} réponses)"
          + (f" ; {len(removed)} ancienne(s) copie(s) supprimée(s)" if removed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
