## Bonnes pratiques pour écrire une question

### Des données vraiment aléatoires
- Tout ce qui peut varier doit varier : valeurs, tailles de listes, **noms** de variables, de
  fonctions, de classes et d'attributs (`randname`, `choice(NOMS_FONCTIONS)`…), opérateurs,
  ordre des instructions, et même la **variante** de l'exercice (`kind = choice([...])`), tant que
  la compétence évaluée reste la même.
- Viser au moins 20 énoncés différents sur 30 tirages (l'éditeur l'affiche). Pour une question
  « écrire une fonction », l'énoncé peut rester proche : ce sont alors les tests cachés qui varient.
- Éviter les cas dégénérés avec `require(...)` : liste vide qui rend la question triviale, deux
  réponses possibles, résultat vide, division par zéro, valeurs identiques qui cachent une erreur.

### Des réponses calculées, jamais écrites à la main
- Pour « qu'affiche ce programme ? », construire le code dans une chaîne `src`, puis
  `out = run(src)` : la réponse est ce que Python affiche réellement.
- Pour « quelle erreur ? », utiliser `run_error(src)` ; pour une valeur finale, `evaluate(src, "x")`
  ou `run(src, namespace=ns)` puis `ns["x"]`.
- En SQL, la réponse est une requête de référence exécutée sur la base générée.

### Des réponses sans ambiguïté
- Dire précisément le format attendu : « écrire la liste comme Python l'afficherait »,
  « séparer les valeurs par des virgules », « sans guillemets », « une valeur par ligne ».
- Pour un champ `text`, activer `ignore_spaces` si les espaces ne comptent pas (listes, binaire),
  `ignore_case` si la casse ne compte pas, `multiline` pour une sortie sur plusieurs lignes, et
  donner une **liste** de réponses acceptées quand plusieurs écritures sont justes
  (`[rep, rep.lstrip('0')]`).
- Un QCM doit avoir une seule bonne réponse (sauf `multiple`) et des distracteurs **plausibles**,
  issus des erreurs fréquentes des élèves : borne de `range` incluse, confusion `/` et `//`,
  indice qui commence à 1, alias au lieu de copie, clé au lieu de valeur, `print` au lieu de
  `return`… Les générer à partir des données (`options` sous forme d'expression).

### Questions de code (champ `code`)
- Tests aléatoires générés dans le code (`cases`), avec des cas limites (liste vide, un seul
  élément, valeurs négatives, doublons).
- Toujours fournir une **solution de référence** : dans un bloc ```python de la `solution`, ou
  dans la clé `reference` du champ. Elle sert à l'auto-test : la question est refusée si la
  référence échoue aux tests, et signalée si une fonction qui ne fait rien les réussit.
- Si le nom de la fonction est tiré au hasard, ne pas utiliser `function` (qui attend un nom
  fixe) : écrire des `tests` qui récupèrent la fonction avec `student.get(fname)`, comme dans
  l'exemple « compter les occurrences ».
- Pour une **classe** écrite par l'élève, les `tests` peuvent l'instancier : `C = student.get("Compte")`,
  puis appeler ses méthodes et vérifier avec `check_equal(...)` (voir l'exemple « Écrire une classe »).
- `forbid` permet d'interdire les raccourcis qui vident l'exercice de son sens (`sum`, `max`,
  `sorted`, `sort`, `count`, `Counter`…).

### Métadonnées
- `chapter` : le chapitre **de la notion évaluée**, pas celui du cours d'où vient l'idée. Une
  question sur les dictionnaires reste dans le chapitre des dictionnaires même si elle a été
  créée à partir du cours de POO : les statistiques par chapitre et le mode automatique restent
  ainsi cohérents.
- `skills` : 1 à 3 compétences courtes et réutilisables, de la forme « Notion : savoir-faire »
  (« Dictionnaires : parcours », « POO : méthodes »). Réutiliser **exactement** les noms déjà
  présents dans le référentiel de l'enseignant quand ils conviennent.
- `difficulty` : 1 application directe, 2 raisonnement en plusieurs étapes, 3 synthèse ou
  écriture de code non guidée.
- `title` : court et unique, il identifie la question dans la banque (« Dictionnaires : parcours »).

### Pièges techniques
- Seules les fonctions aléatoires fournies (ou le module `random`) sont autorisées : pas d'heure,
  pas de `os.urandom`, sinon la correction ne retrouve pas les mêmes données.
- Dans un f-string contenant du code avec des accolades (dictionnaires, ensembles), doubler les
  accolades littérales `{{ }}` ; ou construire le code par concaténation / `repr(d)`.
- Dans le JSON, le code est une chaîne : les sauts de ligne s'écrivent `\n` et les guillemets
  doubles `\"`. Vérifier que le fichier est un JSON valide.
- Le texte de l'énoncé est du Markdown : pas de HTML. Les `{{ }}` de l'énoncé contiennent des
  **expressions** Python (pas d'instructions).
