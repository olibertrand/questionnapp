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
| `fondamentaux-parcours.json` | séries « Comptage », « Recherche » et « Maximum » : fonctions à compléter ou à écrire, uniquement avec `for` (sur les éléments, sur les indices ou au choix) ; listes de nombres et de dictionnaires |
| `remediation-parcours.json` | remédiation, très guidée (code à compléter, boucles `for` uniquement) : afficher les éléments d'une liste, afficher une valeur dans une liste de dictionnaires, `somme(L)`, somme d'une clé (ticket de caisse…), `nb_pairs(L)` |
| `poo.json` | créer un objet, attributs, appeler et écrire des méthodes (classes `Duree`, `Fraction`, `Rectangle`, `Compte`), références |
| `listes-chainees.json` | listes chaînées (classes `Maillon`/`Chaine`, répertoire `Fiche`/`Repertoire`) : liens, création, parcours, méthodes |
| `arbres-binaires.json` | arbres binaires (classe `Arbre`, arbre vide = `None`) : lire et créer un arbre, `taille`, `hauteur`, somme, minimum/maximum en récursif |
| `algorithmique.json` | tris, dichotomie, complexité |
| `representation-donnees.json` | bases 2 et 16, complément à deux, booléens |
| `bases-de-donnees.json` | modèle relationnel, SQL |
| `python-premiere-while.json` | série 1ère NSI : listes, listes de listes et de dictionnaires, dictionnaires, parcours (afficher, compter, cumuler, chercher, « tous »), fonctions simples, portée ; **boucles `while` uniquement** |

## Parcourir toutes les questions

```
python3 scripts/catalogue.py
```

Ce script écrit `catalogue-questions.html` : une seule page à ouvrir dans un navigateur, même
sans connexion. Elle contient toutes les questions de ce répertoire, classées par banque, avec un
sommaire et une recherche. Chaque question y figure avec un exemple tiré par le moteur :
l'énoncé et la zone de réponse tels que l'élève les voit, puis, à déplier, la réponse attendue,
la solution et les indices. Pour obtenir d'autres exemples : `--graine 2` ; pour choisir le
fichier écrit : `--sortie chemin/catalogue.html`. Relancez le script après chaque ajout de
questions.

## Ajouter des questions

- **Déposer un fichier** : copiez ici un fichier au format d'import (par exemple celui produit
  par votre projet Claude, voir `claude-projet/`). Il apparaît aussitôt dans le menu Banques.
- **Compléter un fichier existant** : ajoutez des questions à la liste `questions`, chacune
  avec un **identifiant** `uid` unique qui suit la numérotation du fichier (`DICO-21`, `POO-03`…).
  Les questions sont reconnues par cet identifiant (à défaut, par leur titre) : une question
  déjà présente dans l'application n'est jamais réimportée.
- Format : `{"format": "questionnapp/questions", "version": 1, "title": "...", "description": "...",
  "questions": [...]}` ; chaque question a `uid`, `title`, `chapter`, `difficulty`, `skills`, `template`
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
