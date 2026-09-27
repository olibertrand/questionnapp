# Banques de questions

Chaque fichier `.json` de ce répertoire est une **banque thématique** de questions à données
aléatoires. L'application les liste dans le menu **Banques** : on y voit, pour chaque question,
si elle est nouvelle, déjà importée ou modifiée dans le fichier depuis l'import, on peut
l'essayer avec **Aperçu**, puis l'importer (ou la mettre à jour) et l'affecter à des classes.

| Fichier | Contenu |
|---|---|
| `python-bases.json` | variables, types, conditions, boucles, entrées/sorties |
| `python-listes-chaines.json` | indices et tranches, parcours, compréhensions |
| `python-dictionnaires.json` | accès, `keys`/`values`/`items`, max/min, calculs cumulatifs, données imbriquées |
| `poo.json` | classes, attributs, méthodes, références |
| `algorithmique.json` | tris, dichotomie, complexité |
| `representation-donnees.json` | bases 2 et 16, complément à deux, booléens |
| `bases-de-donnees.json` | modèle relationnel, SQL |

## Ajouter des questions

- **Déposer un fichier** : copiez ici un fichier au format d'import (par exemple celui produit
  par votre projet Claude, voir `claude-projet/`). Il apparaît aussitôt dans le menu Banques.
- **Compléter un fichier existant** : ajoutez des questions à la liste `questions`. Les
  questions sont reconnues par leur **titre**, qui doit donc être unique.
- Format : `{"format": "questionnapp/questions", "version": 1, "title": "...", "description": "...",
  "questions": [...]}` ; chaque question a `title`, `chapter`, `difficulty`, `skills`, `template`
  (voir `docs/QUESTION_FORMAT.md`).

## Modifier ou retirer des questions

- Si vous modifiez une question dans un fichier, elle apparaît « modifiée dans le fichier » :
  la mettre à jour crée une nouvelle version dans l'application (les réponses déjà données par
  les élèves restent consultables).
- Retirer une question d'un fichier ne la supprime pas de l'application (elle garde ses
  statistiques) : pour ne plus la proposer aux élèves, **archivez-la** depuis l'éditeur
  (bouton Supprimer : elle est archivée si des élèves y ont répondu).
- Pour enregistrer dans un fichier des questions créées ou modifiées dans l'application :
  page Questions, cochez-les, **Exporter (JSON)**, puis placez le fichier ici.

## Vérification

`python3 -m unittest tests.test_banque` vérifie chaque fichier : format, titres uniques, et
auto-test de chaque question sur 30 tirages (génération, variété, correction de référence
acceptée, tests de code non triviaux). Pour tester un fichier seul :
`python3 claude-projet/questionnapp_moteur.py banque/mon-fichier.json --apercu`.

Le répertoire utilisé peut être changé avec la variable `QUESTIONNAPP_BANK_DIR`.
