#!/usr/bin/env python3
"""Restauration d'une sauvegarde de la base de QuestionnApp.

  python3 scripts/restaurer.py                       liste les sauvegardes disponibles
  python3 scripts/restaurer.py --test FICHIER        TEST sans risque : restaure dans une copie à
                                                     part et vérifie qu'elle s'ouvre (la vraie base
                                                     n'est pas touchée)
  python3 scripts/restaurer.py FICHIER               remplace la base par la sauvegarde (serveur
                                                     ARRÊTÉ ; demande confirmation)

Avant tout remplacement, la base actuelle est elle-même mise de côté
(data/avant-restauration-AAAA-MM-JJ_HHMMSS.db) : une restauration se défait.
"""

import argparse
import datetime
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config, db  # noqa: E402
from scripts.sauvegarde import NAME_RE, backup, default_dir, summary  # noqa: E402


def copy_db(src_path, dst_path):
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def check_opens(path):
    """La copie restaurée s'ouvre avec l'application (migrations comprises) ?"""
    conn = db.connect(path)
    try:
        db.init(conn)
        return {t: db.one(conn, f"SELECT count(*) AS n FROM {t}")["n"]
                for t in ("users", "classes", "questions", "attempts", "assignments")}
    finally:
        conn.close()


def list_backups(folder):
    if not os.path.isdir(folder):
        print(f"Aucune sauvegarde : le dossier {folder} n'existe pas.")
        return 1
    names = sorted((n for n in os.listdir(folder) if NAME_RE.match(n)), reverse=True)
    if not names:
        print(f"Aucune sauvegarde dans {folder}.")
        return 1
    print(f"Sauvegardes dans {folder} (de la plus récente à la plus ancienne) :")
    for n in names:
        print(f"  {n}  ({os.path.getsize(os.path.join(folder, n)) / 1024:.0f} Ko)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Restauration d'une sauvegarde de QuestionnApp")
    parser.add_argument("fichier", nargs="?", help="sauvegarde à restaurer (chemin ou nom dans le dossier des sauvegardes)")
    parser.add_argument("--test", action="store_true", help="restaurer dans une copie à part, sans toucher à la vraie base")
    parser.add_argument("--dossier", default=None, help="dossier des sauvegardes")
    parser.add_argument("--oui", action="store_true", help="ne pas demander de confirmation")
    args = parser.parse_args(argv)
    folder = args.dossier or default_dir()
    if not args.fichier:
        return list_backups(folder)
    path = args.fichier if os.path.exists(args.fichier) else os.path.join(folder, args.fichier)
    if not os.path.exists(path):
        print(f"Sauvegarde introuvable : {args.fichier}")
        return 1
    try:
        counts = summary(path)
    except Exception as exc:  # noqa: BLE001
        print(f"Cette sauvegarde est abîmée ou illisible : {exc}")
        return 1
    print(f"Sauvegarde : {path}")
    print(f"  {counts['users']} comptes, {counts['questions']} questions, {counts['attempts']} réponses")

    if args.test:
        with tempfile.TemporaryDirectory(prefix="qa-test-restauration-") as tmp:
            target = os.path.join(tmp, "restauration.db")
            copy_db(path, target)
            result = check_opens(target)
        print("TEST RÉUSSI : la sauvegarde se restaure et s'ouvre avec l'application "
              f"({result['users']} comptes, {result['classes']} classes, {result['questions']} questions, "
              f"{result['attempts']} réponses, {result['assignments']} séances).")
        print("La vraie base n'a pas été modifiée.")
        return 0

    print(f"Base actuelle qui sera REMPLACÉE : {config.DB_PATH}")
    print("Le serveur de l'application doit être arrêté pendant la restauration.")
    if not args.oui and input("Confirmer en tapant « oui » : ").strip().lower() != "oui":
        print("Annulé.")
        return 1
    if os.path.exists(config.DB_PATH):
        stamp = f"{datetime.datetime.now():%Y-%m-%d_%H%M%S}"
        aside = os.path.join(os.path.dirname(os.path.abspath(config.DB_PATH)), f"avant-restauration-{stamp}.db")
        copy_db(config.DB_PATH, aside)
        print(f"Base actuelle mise de côté : {aside}")
    copy_db(path, config.DB_PATH)
    result = check_opens(config.DB_PATH)
    print(f"Restauration terminée ({result['users']} comptes, {result['attempts']} réponses). Redémarrez l'application.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
