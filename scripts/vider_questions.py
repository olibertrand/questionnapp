#!/usr/bin/env python3
"""Vide la banque de questions de l'application (à lancer serveur arrêté).

  python3 scripts/vider_questions.py          (demande confirmation)
  python3 scripts/vider_questions.py --oui    (sans confirmation)

Supprime : toutes les questions et leurs versions, les réponses des élèves, les séances,
les chapitres et les compétences. Conserve : les comptes, les classes et leurs membres,
l'historique des connexions. Les questions pourront ensuite être réimportées depuis le
menu Banques (répertoire banque/).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config, db  # noqa: E402


def main():
    if not os.path.exists(config.DB_PATH):
        print(f"Aucune base trouvée ({config.DB_PATH}).")
        return 1
    conn = db.connect()
    db.init(conn)
    counts = {t: db.one(conn, f"SELECT count(*) AS n FROM {t}")["n"]
              for t in ("questions", "attempts", "assignments", "chapters", "skills")}
    print(f"Base : {config.DB_PATH}")
    print(f"À supprimer : {counts['questions']} question(s), {counts['attempts']} réponse(s) d'élèves, "
          f"{counts['assignments']} séance(s), {counts['chapters']} chapitre(s), {counts['skills']} compétence(s).")
    print("Conservés : comptes, classes et leurs membres, connexions.")
    if "--oui" not in sys.argv:
        if input("Confirmer en tapant « oui » : ").strip().lower() != "oui":
            print("Annulé.")
            return 1
    with db.Tx(conn):
        for table in ("attempts", "assignment_questions", "assignments", "class_questions", "question_skills",
                      "question_versions", "questions", "skills", "chapters"):
            conn.execute(f"DELETE FROM {table}")
    conn.execute("VACUUM")
    conn.close()
    print("Banque de questions vidée. Réimportez les questions depuis le menu Banques.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
