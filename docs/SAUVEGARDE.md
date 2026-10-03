# Sauvegarde et restauration de la base

Toutes les données (comptes, classes, questions, réponses des élèves, statistiques) sont dans
**un seul fichier SQLite** : `data/questionnapp.db` par défaut, ou le chemin donné par la
variable `QUESTIONNAPP_DB`. Le sauvegarder suffit.

## 1. Sauvegarder

```sh
python3 scripts/sauvegarde.py
```

- La copie est sûre **même pendant les cours** : pas besoin d'arrêter l'application. (Ne pas
  utiliser un simple `cp`, qui peut produire une copie incomplète pendant que l'appli écrit.)
- Chaque copie est vérifiée avant d'être gardée.
- Les copies vont dans `data/sauvegardes/` (ou le dossier de `QUESTIONNAPP_BACKUP_DIR`, ou
  `--dossier /chemin`), sous le nom `questionnapp-AAAA-MM-JJ_HHMMSS.db`.
- Rotation automatique : la dernière copie de chacun des **14 derniers jours** et de chacun des
  **12 derniers mois** est gardée (`--jours N`, `--mois N` pour changer) ; les plus anciennes
  sont supprimées. Les autres fichiers du dossier ne sont jamais touchés.

## 2. Sauvegarder automatiquement chaque nuit (cron)

Sur le serveur, ouvrir le planificateur de tâches de l'utilisateur qui fait tourner l'appli :

```sh
crontab -e
```

et ajouter cette ligne (en remplaçant `/chemin/vers/questionnapp` par le dossier du projet) :

```
17 2 * * * cd /chemin/vers/questionnapp && python3 scripts/sauvegarde.py >> data/sauvegardes.log 2>&1
```

La sauvegarde se lance alors chaque nuit à 2 h 17 et note son résultat dans
`data/sauvegardes.log`.

- Si l'application est lancée avec `QUESTIONNAPP_DB=...` (dans un service systemd, un script…),
  mettre la même variable dans la ligne cron :
  `17 2 * * * cd /chemin/vers/questionnapp && QUESTIONNAPP_DB=/chemin/base.db python3 scripts/sauvegarde.py >> ...`
- Le lendemain, vérifier que ça a marché : `tail data/sauvegardes.log` doit montrer une ligne
  « sauvegarde OK », et `python3 scripts/restaurer.py` liste les copies.

## 3. Tester une sauvegarde (à faire au moins une fois)

```sh
python3 scripts/restaurer.py                          # liste les sauvegardes
python3 scripts/restaurer.py --test questionnapp-2026-10-03_021700.db
```

Le test restaure la copie **dans un fichier à part** et vérifie que l'application l'ouvre ; il
affiche le nombre de comptes, classes, questions et réponses. **La vraie base n'est pas
modifiée.** Les chiffres doivent correspondre à ce qu'on voit dans l'appli.

Pour aller jusqu'au bout, on peut aussi lancer une seconde appli sur une copie, sur un autre
port, et s'y connecter :

```sh
cp data/sauvegardes/questionnapp-2026-10-03_021700.db /tmp/essai.db
QUESTIONNAPP_DB=/tmp/essai.db QUESTIONNAPP_PORT=8001 python3 run.py
```

## 4. Restaurer en cas de problème

1. **Arrêter l'application.**
2. `python3 scripts/restaurer.py questionnapp-AAAA-MM-JJ_HHMMSS.db` puis taper `oui`.
   La base actuelle est d'abord mise de côté (`data/avant-restauration-….db`) : on peut revenir
   en arrière.
3. Redémarrer l'application.

Tout ce qui a été fait entre la sauvegarde et la restauration (réponses des élèves, questions
créées) est perdu : choisir la copie la plus récente qui est saine.

## Limite actuelle

Les copies sont sur le **même serveur** que l'application : elles protègent contre une erreur
ou un fichier abîmé, pas contre la perte du serveur lui-même. Pour s'en protéger, copier aussi
régulièrement le dossier `data/sauvegardes/` sur une autre machine.
