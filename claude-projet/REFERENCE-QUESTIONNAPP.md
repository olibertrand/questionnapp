# Référence QuestionnApp pour la création de questions

> Fichier généré par `scripts/build_claude_project.py` — ne pas modifier à la main.

## Format des questions

Une question est un **modèle** (template) : du code Python tire des données au hasard et
calcule les réponses ; l'énoncé et la correction sont du Markdown où `{{ expression }}`
insère une valeur. Chaque élève — et chaque nouvelle tentative — reçoit donc des données
différentes, mais le même type d'exercice et les mêmes compétences.

Le modèle est stocké en JSON (`question_versions.template`) :

```json
{
  "code": "a = randint(2, 9)\nn = randint(3, 6)\nsrc = f'''s = 0\nfor i in range({n}):\n    s = s + {a}\nprint(s)'''\nsortie = run(src)",
  "statement": "Qu'affiche le programme suivant ?\n\n{{ code_block(src) }}",
  "fields": [ { "type": "text", "label": "Affichage", "answer": "sortie" } ],
  "solution": "La boucle ajoute {{ a }} à `s`, {{ n }} fois : le programme affiche **{{ sortie }}**."
}
```

Clés facultatives : `hints` (liste d'indices, voir § 3 bis) et `max_tries` (nombre d'essais).
Les métadonnées (titre, chapitre, compétences, difficulté, classes) sont gérées à part, dans la base.

### 1. Le générateur (`code`)

Du Python ordinaire, exécuté avec une **graine** : la même graine redonne exactement la
même question (c'est ce qui permet de corriger côté serveur sans jamais envoyer la réponse
au navigateur). Toutes les variables définies sont ensuite utilisables dans l'énoncé, les
intitulés, les réponses et la correction.

### Fonctions aléatoires (liées à la graine)

| Fonction | Rôle |
|---|---|
| `randint(a, b)` | entier dans [a, b] |
| `randnz(a, b)` | entier non nul dans [a, b] |
| `choice(seq)` | un élément |
| `sample(seq, k)` | k éléments distincts |
| `shuffled(seq)` | copie mélangée |
| `randlist(n, a, b, distinct=False)` | liste de n entiers |
| `randword(longueur)` | mot aléatoire |
| `randname(pool=None, k=None)` | nom(s) de variable (par défaut dans `NOMS_VARIABLES`) |
| `coin(p=0.5)` | booléen |
| `uniform(a, b)`, `randrange(...)`, `random` | comme le module `random` |
| `require(cond)` / `reject()` | contrainte : si elle échoue, on retire toutes les valeurs (200 essais max) |

Listes prêtes à l'emploi : `PRENOMS`, `FRUITS`, `VILLES`, `NOMS_VARIABLES`, `NOMS_LISTES`, `NOMS_FONCTIONS`.

> N'utilisez pas d'autre source d'aléa (heure, `os.urandom`…) : l'éditeur signale un
> générateur non déterministe. Un `import random` reste possible (le module est seedé aussi).

### Exécuter du code (questions « qu'affiche ce programme ? »)

| Fonction | Rôle |
|---|---|
| `run(code, inputs=None, namespace=None)` | exécute `code` et renvoie ce qu'il affiche (sans le `\n` final). `inputs` : valeurs renvoyées par `input()`. Si `namespace={}` est fourni, les variables du programme y restent. |
| `run_error(code)` | nom de l'exception levée (`"IndexError"`…) ou `None` |
| `evaluate(code, expr)` | exécute `code` puis renvoie la valeur de `expr` |
| `dedent(code)`, `indent(code, n)` | mise en forme |
| `code_block(code, lang="python")` | bloc de code Markdown |

### Bases de données

| Fonction | Rôle |
|---|---|
| `sql_insert(table, lignes)` | script `INSERT` |
| `sql_table(setup, table)` | contenu d'une table en tableau Markdown |
| `sql_schema(setup)` | schéma relationnel (clés primaires soulignées, clés étrangères fléchées) |
| `sql_run(setup, requête)` / `sql_value(...)` | résultat d'une requête (SQLite en mémoire) |
| `md_table(lignes, entêtes)` | tableau Markdown quelconque |

### Représentation des données / architecture

`tobase(n, base, largeur=0)`, `frombase(s, base)`, `twos(n, bits)` (complément à deux),
`from_twos(s)`, `group("10110011")` → `"1011 0011"`, `fr(x, décimales)` (virgule décimale).

Modules disponibles directement : `math`, `string`, `textwrap` ; importables : `random`,
`itertools`, `collections`, `functools`, `re`, `heapq`, `bisect`, `statistics`, `fractions`,
`decimal`, `copy`, `json`, `datetime`, `sqlite3`… (liste dans `engine/sandbox.py`).

### 2. Énoncé, intitulés, correction

Markdown (sous-ensemble) : paragraphes, `**gras**`, `*italique*`, `` `code` ``, blocs
```` ```python ````, listes, citations `>`, tableaux `| a | b |`, titres, liens.
`{{ expression }}` est remplacé par la valeur de l'expression Python (les flottants entiers
s'affichent sans `.0`).

### 3. Champs de réponse (`fields`)

Une question peut avoir plusieurs champs ; le score est la moyenne des scores des champs.
Clés communes : `type`, `label` (Markdown avec `{{ }}`).
Les clés `answer`, `options` (forme expression), `setup`, `cases` sont des **expressions
Python** évaluées dans l'espace du générateur.

### `number`
| clé | défaut | rôle |
|---|---|---|
| `answer` | — | valeur attendue |
| `tolerance` | 0 | écart absolu toléré |
| `suffix` | "" | unité affichée après la case |

L'élève peut écrire `3,5`, `3.5`, `1 000`, `7/2`. Les expressions (`3*4`) sont refusées.

### `text`
| clé | défaut | rôle |
|---|---|---|
| `answer` | — | une chaîne, ou une **liste** de chaînes acceptées |
| `multiline` | false | zone de saisie sur plusieurs lignes (sortie de programme) |
| `ignore_case` | false | ignorer majuscules/minuscules |
| `ignore_spaces` | false | ignorer tous les espaces (`[1, 2]` = `[1,2]`) |
| `ignore_accents` | false | ignorer les accents |

Toujours : espaces de début/fin et de fin de ligne ignorés, sauts de ligne normalisés.

### `choice` (QCM)
| clé | défaut | rôle |
|---|---|---|
| `options` | — | liste `[{"text": "...", "correct": true}]` (où `correct` peut être une condition Python en chaîne) **ou** expression donnant une liste de couples `(texte, correct)` |
| `multiple` | false | plusieurs bonnes réponses (cases à cocher, score partiel) |
| `shuffle` | true | mélanger les options |

Deux options identiques après tirage déclenchent un nouveau tirage des valeurs.

### `code` (Python écrit par l'élève)
| clé | rôle |
|---|---|
| `starter` | code de départ (Markdown non interprété, `{{ }}` autorisés) |
| `reference` | solution de référence (`{{ }}` autorisés) utilisée par l'auto-test ; à défaut, le premier bloc ```python de la correction |
| `function` + `cases` | nom de la fonction à tester et expression donnant `[((arg1, arg2), attendu), ...]` |
| `tests` | code Python supplémentaire ; y utiliser `check(cond, message)` et `check_equal(obtenu, attendu, message)`. Y sont visibles : les variables du générateur, les définitions de l'élève, `student` (son espace de noms) et `student_output` (ce que son programme a affiché). |
| `forbid` | noms interdits (`"sum"`, `"sorted"`, `"sort"`, `"import"`, `"while"`, `"for"`…) |
| `time_limit` | secondes (défaut 2) |
| `all_or_nothing` | sinon score = proportion de tests réussis |
| `show_tests` | afficher les tests échoués (défaut true) |

Restrictions du code élève : imports limités (`math`, `random`, `itertools`, `collections`,
`functools`, `string`, `re`, `heapq`, `bisect`, `statistics`, `fractions`, `decimal`, `copy`…),
pas d'`eval`/`exec`/`open`/`input`, pas d'attributs internes (`__class__`, `__globals__`,
`_x` hors `self._x`…), pas d'introspection des frames. Les méthodes spéciales usuelles
(`__init__`, `__str__`, `__eq__`, `__lt__`…) restent utilisables.

Comparaison stricte des résultats (un objet dont `__eq__` renvoie toujours `True` ne passe pas ;
entiers et flottants comparés à 1e-9 près). Les arguments sont copiés avant chaque appel.

### `sql`
| clé | rôle |
|---|---|
| `setup` | expression donnant le script de création de la base |
| `answer` | expression donnant la requête de référence |
| `ordered` | l'ordre des lignes compte (défaut false) |
| `starter` | requête de départ |

La requête de l'élève est exécutée sur une base neuve ; on compare les lignes obtenues
(multiensemble, flottants arrondis à 1e-6) à celles de la référence. Les noms de colonnes ne
comptent pas. En cas d'erreur, l'élève voit un indice (nombre de lignes / colonnes attendu)
et un aperçu de son résultat.

### 3 bis. Essais et indices

L'élève peut se corriger : après une réponse fausse, il voit quels champs sont justes ou faux
et les commentaires de correction (tests de code qui échouent, nombre de lignes attendu en
SQL…), **mais pas la solution**. Les champs justes sont verrouillés.

| clé | défaut | rôle |
|---|---|---|
| `max_tries` | 3 (1 pour un QCM à deux options) | nombre d'essais avant que la solution ne s'affiche |
| `hints` | [] | liste d'indices (Markdown, `{{ }}` autorisés) : le 1er après la 1re erreur, le 2e après la 2e… |

Sans `hints`, un conseil générique adapté au type des champs faux est affiché. Un bon indice
s'appuie sur les données du tirage (« `range({{ a }}, {{ b }})` s'arrête avant {{ b }} ») et
oriente vers la méthode sans donner la réponse ; le dernier peut être plus précis.

La question se termine sur une bonne réponse, quand les essais sont épuisés, ou si l'élève
demande la solution. Score enregistré : score du dernier essai × 100 % (1er essai), 75 % (2e),
50 % (3e), 25 % ensuite. Une réponse vide n'est pas comptée comme un essai.

### 4. Variété et « jamais deux fois la même question »

* L'empreinte d'une instance est le SHA-256 (16 premiers caractères hexadécimaux) du JSON
  canonique de sa partie publique (énoncé + champs, clés triées).
* Au moment de servir une question, le serveur évite les empreintes **déjà vues par cet élève**
  et celles **servies à n'importe qui dans les 3 dernières heures** (deux voisins n'ont pas les
  mêmes données) : jusqu'à 25 graines sont essayées.
* L'éditeur indique combien d'énoncés différents apparaissent sur 30 tirages. Pour une
  question « écrire une fonction », l'énoncé peut rester identique : ce sont les tests cachés
  qui changent.

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

### Indices (clé `hints`)
- L'élève dispose de plusieurs essais (3 par défaut) ; après chaque erreur il reçoit l'indice
  suivant, sans la solution. Écrire **2 indices** par question, du plus général au plus précis.
- Un bon indice s'appuie sur les données du tirage (`{{ }}`) et rappelle la méthode ou le piège
  classique (« `range({{ a }}, {{ b }})` s'arrête **avant** {{ b }} », « `{{ o2 }} = {{ o1 }}` ne copie
  pas l'objet »), sans jamais donner la réponse.
- Pour une question de code, les tests qui échouent servent déjà d'indice : les `hints` peuvent
  rappeler la méthode (initialiser un accumulateur, cas de la liste vide…).
- `max_tries` n'est à préciser que pour changer le défaut (par exemple 1 pour un QCM où un second
  essai reviendrait à donner la réponse).

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

## Fichier d'import et questions d'exemple

Le fichier à produire a exactement cette structure (`format`, `version`, puis la liste `questions`). Chaque question : `title`, `chapter`, `difficulty` (1 facile, 2 moyen, 3 difficile), `skills` (liste), `template`. Voici les 25 questions d'exemple de l'application, toutes testées : elles montrent les bons usages de chaque type de champ.

```json
{
  "format": "questionnapp/questions",
  "version": 1,
  "questions": [
    {
      "title": "Suivre l'évolution de variables",
      "chapter": "Python : les bases",
      "difficulty": 1,
      "skills": [
        "Tracer l'exécution d'un programme",
        "Affectation"
      ],
      "template": {
        "code": "a, b = randint(2, 9), randint(2, 9)\nx, y = randname(k=2)\nops = shuffled([f\"{x} = {x} + {y}\", f\"{y} = {x} * 2\", f\"{x} = {y} - {x}\", f\"{y} = {y} + 1\"])[:3]\nsrc = f\"{x} = {a}\\n{y} = {b}\\n\" + \"\\n\".join(ops)\nns = {}\nrun(src, namespace=ns)\nvx, vy = ns[x], ns[y]",
        "statement": "On exécute le programme suivant :\n\n{{ code_block(src) }}\n\nQuelles sont les valeurs de `{{ x }}` et `{{ y }}` à la fin ?",
        "fields": [
          {
            "type": "number",
            "label": "Valeur de `{{ x }}`",
            "answer": "vx"
          },
          {
            "type": "number",
            "label": "Valeur de `{{ y }}`",
            "answer": "vy"
          }
        ],
        "solution": "À la fin : `{{ x }} = {{ vx }}` et `{{ y }} = {{ vy }}`. Pensez à noter les valeurs ligne par ligne dans un tableau.",
        "hints": [
          "Faites un tableau avec une colonne pour `{{ x }}` et une pour `{{ y }}`, et remplissez une ligne par instruction.",
          "Dans `{{ ops[0] }}`, la partie droite est calculée avec les valeurs **d'avant** l'instruction, puis rangée dans la variable de gauche."
        ]
      }
    },
    {
      "title": "Boucle for et range",
      "chapter": "Python : les bases",
      "difficulty": 2,
      "skills": [
        "Boucle for",
        "Fonction range"
      ],
      "template": {
        "code": "start = randint(0, 5)\nstop = start + randint(6, 15)\nstep = choice([1, 2, 3])\nacc = choice([\"s\", \"total\", \"somme\", \"res\"])\nop = choice([\"+\", \"*\"]) if stop - start < 8 and step > 1 else \"+\"\ninit = 0 if op == \"+\" else 1\nsrc = f\"{acc} = {init}\\nfor i in range({start}, {stop}, {step}):\\n    {acc} = {acc} {op} i\\nprint({acc})\"\nif op == \"*\":\n    src = src.replace(f\"range({start}\", f\"range({max(start, 1)}\")\nout = run(src)\nvals = list(range(max(start, 1) if op == \"*\" else start, stop, step))",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Affichage",
            "answer": "int(out)"
          }
        ],
        "solution": "`i` prend successivement les valeurs {{ vals }} (la borne {{ stop }} est exclue). Le programme affiche **{{ out }}**.",
        "hints": [
          "`i` commence à {{ vals[0] }}, avance de {{ step }} en {{ step }} et s'arrête **avant** {{ stop }} : écrivez la liste des valeurs prises par `i`.",
          "Les valeurs de `i` sont {{ vals[:3] }}… : il reste à les combiner une par une avec `{{ acc }}`."
        ]
      }
    },
    {
      "title": "Type d'une expression",
      "chapter": "Python : les bases",
      "difficulty": 1,
      "skills": [
        "Types de base"
      ],
      "template": {
        "code": "a, b = randint(2, 9), randint(2, 9)\npool = [\n    (f\"{a * b} / {b}\", \"float\"), (f\"{a * b + 1} // {b}\", \"int\"), (f\"{a} % {b}\", \"int\"),\n    (f\"'{a}' * {b}\", \"str\"), (f\"[{a}] * {b}\", \"list\"), (f\"{a} == {a}.0\", \"bool\"),\n    (f\"str({a}) + '{b}'\", \"str\"), (f\"{a} ** 2\", \"int\"), (f\"{a} + {b}.0\", \"float\"),\n    (f\"len('{randword()}')\", \"int\"), (f\"({a}, {b})\", \"tuple\"), (f\"{a} < {b} or {a} > {b}\", \"bool\"),\n]\nexpr, ty = choice(pool)\nvalue = eval(expr)",
        "statement": "Quel est le type de la valeur de l'expression `{{ expr }}` ?",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "[(t, t == ty) for t in ['int', 'float', 'str', 'bool', 'list', 'tuple']]"
          }
        ],
        "solution": "`{{ expr }}` vaut `{{ repr(value) }}`, de type `{{ ty }}`."
      }
    },
    {
      "title": "Instructions conditionnelles",
      "chapter": "Python : les bases",
      "difficulty": 1,
      "skills": [
        "Conditions if/elif/else"
      ],
      "template": {
        "code": "x = randint(-20, 30)\ns1, s2 = sorted(sample(range(-10, 25), 2))\nw = sample([\"froid\", \"doux\", \"chaud\", \"tiède\", \"glacial\", \"bon\"], 3)\nsrc = dedent(f'''\nt = {x}\nif t < {s1}:\n    print(\"{w[0]}\")\nelif t < {s2}:\n    print(\"{w[1]}\")\nelse:\n    print(\"{w[2]}\")\n''')\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage (sans les guillemets)",
            "answer": "out",
            "ignore_case": true
          }
        ],
        "solution": "Avec `t = {{ x }}`, le programme affiche `{{ out }}`."
      }
    },
    {
      "title": "Saisie et conversion (input)",
      "chapter": "Python : les bases",
      "difficulty": 2,
      "skills": [
        "Entrées/sorties",
        "Types de base"
      ],
      "template": {
        "code": "a, b = randint(2, 30), randint(2, 30)\nconv = choice([\"int\", \"str\"])\nif conv == \"int\":\n    src = \"x = int(input())\\ny = int(input())\\nprint(x + y)\"\nelse:\n    src = \"x = input()\\ny = input()\\nprint(x + y)\"\nout = run(src, inputs=[a, b]).split(\"\\n\")[-1]",
        "statement": "L'utilisateur tape `{{ a }}` puis `{{ b }}` (chacun suivi d'Entrée). Qu'affiche le programme à la fin ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Dernière ligne affichée",
            "answer": "out"
          }
        ],
        "solution": "`input()` renvoie toujours une **chaîne**. {{ \"Avec la conversion en entier, on additionne des nombres\" if conv == \"int\" else \"Sans conversion, `+` concatène les chaînes\" }} : le programme affiche `{{ out }}`."
      }
    },
    {
      "title": "Indices et tranches",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Listes : indices et tranches"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nT = randlist(randint(6, 9), 1, 50, distinct=True)\nn = len(T)\ni = randint(1, n - 3)\nj = randint(i + 1, n - 1)\nkind = choice([\"tranche\", \"négatif\", \"pas\"])\nif kind == \"tranche\":\n    expr = f\"{nom}[{i}:{j}]\"\nelif kind == \"négatif\":\n    expr = f\"{nom}[-{randint(1, n - 1)}]\"\nelse:\n    expr = f\"{nom}[{choice(['', str(i)])}::{choice([2, 3, -1])}]\"\nres = eval(expr, {nom: T})",
        "statement": "On définit `{{ nom }} = {{ T }}`.\n\nQue vaut `{{ expr }}` ? (écrire la valeur comme Python l'afficherait)",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "repr(res)",
            "ignore_spaces": true
          }
        ],
        "solution": "`{{ expr }}` vaut `{{ repr(res) }}`. Rappel : les indices commencent à 0, la borne de fin d'une tranche est exclue.",
        "hints": [
          "Les indices commencent à 0 : `{{ nom }}[0]` vaut {{ T[0] }}. Numérotez les éléments avant de répondre.",
          "Dans une tranche `[début:fin:pas]`, l'élément d'indice `fin` n'est **pas** inclus ; un indice négatif compte à partir de la fin (`-1` est le dernier)."
        ]
      }
    },
    {
      "title": "Écrire une fonction : compter les occurrences",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Écrire une fonction",
        "Parcours de liste"
      ],
      "template": {
        "code": "fname = choice([\"compte\", \"occurrences\", \"nb_occ\", \"nombre\", \"frequence\"])\nx0 = randint(1, 9)\ndef ref(L, x):\n    return sum(1 for e in L if e == x)\ncases = []\nfor _ in range(6):\n    L = randlist(randint(0, 10), 0, 5)\n    x = randint(0, 5)\n    cases.append(((L, x), ref(L, x)))",
        "statement": "Écrire une fonction `{{ fname }}(L, x)` qui renvoie le nombre de fois où la valeur `x` apparaît dans la liste `L`.\n\nLa méthode `count` est **interdite**.\n\nExemple : `{{ fname }}([{{ x0 }}, 2, {{ x0 }}, 3], {{ x0 }})` renvoie `{{ 2 if x0 != 2 else 3 }}`.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "forbid": [
              "count"
            ],
            "starter": "def {{ fname }}(L, x):\n    ",
            "tests": "fn = student.get(fname)\ncheck(callable(fn), f'la fonction {fname} doit être définie')\nif callable(fn):\n    for (L, x), attendu in cases:\n        check_equal(fn(list(L), x), attendu, f'{fname}({L}, {x}) doit renvoyer {attendu}')"
          }
        ],
        "solution": "```python\ndef {{ fname }}(L, x):\n    n = 0\n    for e in L:\n        if e == x:\n            n = n + 1\n    return n\n```"
      }
    },
    {
      "title": "Compréhension de liste",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Listes en compréhension"
      ],
      "template": {
        "code": "a, b = sorted(sample(range(0, 12), 2))\nk = randint(2, 4)\nf = choice([\"x * x\", f\"x * {k}\", f\"x + {k}\", f\"x // {k}\"])\ncond = choice([f\"x % {k} == 0\", \"x % 2 == 1\", f\"x > {a + 1}\", None])\nexpr = f\"[{f} for x in range({a}, {b + 3})\" + (f\" if {cond}\" if cond else \"\") + \"]\"\nres = eval(expr)\nrequire(0 < len(res) <= 8)",
        "statement": "Que vaut la liste `{{ expr }}` ?",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "repr(res)",
            "ignore_spaces": true
          }
        ],
        "solution": "On obtient `{{ res }}`."
      }
    },
    {
      "title": "Parcours d'une chaîne",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Chaînes de caractères",
        "Boucle for"
      ],
      "template": {
        "code": "mot = choice([\"informatique\", \"algorithme\", \"programmation\", \"ordinateur\", \"variable\", \"processeur\", \"boucle\", \"fonction\"])\nv = choice([\"aeiouy\", \"aeiou\"])\nkind = choice([\"voyelles\", \"inverse\", \"positions\"])\nif kind == \"voyelles\":\n    src = f\"mot = '{mot}'\\nn = 0\\nfor c in mot:\\n    if c in '{v}':\\n        n = n + 1\\nprint(n)\"\nelif kind == \"inverse\":\n    src = f\"mot = '{mot}'\\nr = ''\\nfor c in mot:\\n    r = c + r\\nprint(r)\"\nelse:\n    src = f\"mot = '{mot}'\\nfor i in range(len(mot)):\\n    if mot[i] == '{choice(sorted(set(mot)))}':\\n        print(i)\"\nout = run(src)",
        "statement": "Qu'affiche ce programme ? (s'il affiche plusieurs lignes, mettre une valeur par ligne)\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "out",
            "multiline": true
          }
        ],
        "solution": "Le programme affiche :\n\n{{ code_block(out, 'text') }}"
      }
    },
    {
      "title": "Tri par sélection : état intermédiaire",
      "chapter": "Algorithmique",
      "difficulty": 2,
      "skills": [
        "Algorithmes de tri",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "T = randlist(randint(6, 8), 1, 40, distinct=True)\nk = randint(1, 3)\nS = list(T)\nfor i in range(k):\n    m = min(range(i, len(S)), key=lambda j: S[j])\n    S[i], S[m] = S[m], S[i]\nrequire(S != sorted(T))",
        "statement": "On applique le **tri par sélection** (on cherche le minimum de la partie non triée et on l'échange avec le premier élément de cette partie) à la liste :\n\n`{{ T }}`\n\nQuelle est la liste après **{{ k }}** passage(s) de la boucle principale ?",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "repr(S)",
            "ignore_spaces": true
          }
        ],
        "solution": "Après {{ k }} passage(s) : `{{ S }}`.",
        "hints": [
          "Au 1er passage, on cherche le minimum de toute la liste ({{ min(T) }}) et on l'échange avec le **premier** élément.",
          "Au passage suivant, on ignore la partie déjà triée au début de la liste et on recommence sur le reste."
        ]
      }
    },
    {
      "title": "Recherche dichotomique : indices consultés",
      "chapter": "Algorithmique",
      "difficulty": 2,
      "skills": [
        "Recherche dichotomique"
      ],
      "template": {
        "code": "n = randint(9, 15)\nT = sorted(randlist(n, 1, 99, distinct=True))\nx = choice(T + [randint(1, 99)])\ng, d, vus = 0, n - 1, []\nwhile g <= d:\n    m = (g + d) // 2\n    vus.append(m)\n    if T[m] == x:\n        break\n    elif T[m] < x:\n        g = m + 1\n    else:\n        d = m - 1\nsrc = dedent('''\ndef dicho(T, x):\n    g, d = 0, len(T) - 1\n    while g <= d:\n        m = (g + d) // 2\n        if T[m] == x:\n            return m\n        elif T[m] < x:\n            g = m + 1\n        else:\n            d = m - 1\n    return -1\n''')",
        "statement": "{{ code_block(src) }}\n\nOn appelle `dicho(T, {{ x }})` avec `T = {{ T }}`.\n\nDonner, dans l'ordre, les valeurs successives prises par `m`, séparées par des virgules.",
        "fields": [
          {
            "type": "text",
            "label": "Valeurs de m",
            "answer": "','.join(map(str, vus))",
            "ignore_spaces": true
          },
          {
            "type": "number",
            "label": "Valeur renvoyée",
            "answer": "T.index(x) if x in T else -1"
          }
        ],
        "solution": "`m` prend les valeurs {{ vus }}. {{ 'La valeur est trouvée à l’indice ' + str(T.index(x)) if x in T else 'La valeur est absente : la fonction renvoie -1' }}.",
        "hints": [
          "Au départ, `g = 0` et `d = {{ n - 1 }}`, donc le premier `m` vaut `({{ 0 }} + {{ n - 1 }}) // 2 = {{ (n - 1) // 2 }}`.",
          "Après chaque comparaison, une seule des deux bornes change : `g = m + 1` si `T[m] < x`, `d = m - 1` sinon."
        ]
      }
    },
    {
      "title": "Complexité d'un algorithme",
      "chapter": "Algorithmique",
      "difficulty": 2,
      "skills": [
        "Complexité"
      ],
      "template": {
        "code": "f = choice(NOMS_FONCTIONS)\ncas = [\n    (\"O(n)\", f\"def {f}(L):\\n    s = 0\\n    for x in L:\\n        s = s + x\\n    return s\"),\n    (\"O(n²)\", f\"def {f}(L):\\n    n = 0\\n    for x in L:\\n        for y in L:\\n            if x < y:\\n                n = n + 1\\n    return n\"),\n    (\"O(log n)\", f\"def {f}(n):\\n    k = 0\\n    while n > 1:\\n        n = n // 2\\n        k = k + 1\\n    return k\"),\n    (\"O(1)\", f\"def {f}(L):\\n    return L[0] + L[-1]\"),\n    (\"O(n²)\", f\"def {f}(L):\\n    for i in range(len(L)):\\n        for j in range(i):\\n            print(L[i], L[j])\"),\n    (\"O(n)\", f\"def {f}(n):\\n    i = 0\\n    while i < {randint(2, 5)} * n:\\n        i = i + 1\\n    return i\"),\n]\nrep, src = choice(cas)",
        "statement": "Quelle est la complexité en temps de cette fonction, en fonction de la taille `n` de son entrée ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "[(c, c == rep) for c in ['O(1)', 'O(log n)', 'O(n)', 'O(n²)']]",
            "shuffle": false
          }
        ],
        "solution": "La complexité est **{{ rep }}**."
      }
    },
    {
      "title": "Écrire une fonction : maximum ou minimum",
      "chapter": "Algorithmique",
      "difficulty": 2,
      "skills": [
        "Écrire une fonction",
        "Parcours de liste"
      ],
      "template": {
        "code": "kind = choice([\"max\", \"min\"])\nfname = choice([\"maximum\", \"plus_grand\", \"le_max\"] if kind == \"max\" else [\"minimum\", \"plus_petit\", \"le_min\"])\nref = max if kind == \"max\" else min\ncases = []\nfor _ in range(6):\n    L = randlist(randint(1, 10), -50, 50)\n    cases.append(((L,), ref(L)))",
        "statement": "Écrire une fonction `{{ fname }}(L)` qui renvoie le plus {{ \"grand\" if kind == \"max\" else \"petit\" }} élément d'une liste **non vide** d'entiers.\n\nLes fonctions `max`, `min` et `sorted` et la méthode `sort` sont interdites.",
        "fields": [
          {
            "type": "code",
            "label": "",
            "forbid": [
              "max",
              "min",
              "sorted",
              "sort"
            ],
            "starter": "def {{ fname }}(L):\n    ",
            "tests": "fn = student.get(fname)\ncheck(callable(fn), f'la fonction {fname} doit être définie')\nif callable(fn):\n    for (L,), attendu in cases:\n        check_equal(fn(list(L)), attendu, f'{fname}({L}) doit renvoyer {attendu}')"
          }
        ],
        "solution": "```python\ndef {{ fname }}(L):\n    m = L[0]\n    for x in L:\n        if x {{ \">\" if kind == \"max\" else \"<\" }} m:\n            m = x\n    return m\n```"
      }
    },
    {
      "title": "Conversions entre bases",
      "chapter": "Représentation des données et architecture",
      "difficulty": 1,
      "skills": [
        "Écriture binaire",
        "Écriture hexadécimale"
      ],
      "template": {
        "code": "n = randint(20, 255)\nsens = choice([\"d2b\", \"b2d\", \"d2h\", \"h2d\"])\nif sens == \"d2b\":\n    q, rep, cible = f\"l'entier {n}\", tobase(n, 2), \"en binaire\"\nelif sens == \"b2d\":\n    q, rep, cible = f\"le nombre binaire {group(tobase(n, 2, 8))}\", str(n), \"en décimal\"\nelif sens == \"d2h\":\n    q, rep, cible = f\"l'entier {n}\", tobase(n, 16), \"en hexadécimal\"\nelse:\n    q, rep, cible = f\"le nombre hexadécimal {tobase(n, 16)}\", str(n), \"en décimal\"",
        "statement": "Écrire {{ q }} {{ cible }} (sans préfixe `0b` ni `0x`).",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "[rep, rep.lstrip('0') or '0', rep.zfill(8)]",
            "ignore_spaces": true,
            "ignore_case": true
          }
        ],
        "solution": "{{ n }} = {{ group(tobase(n, 2, 8)) }} en binaire = {{ tobase(n, 16) }} en hexadécimal.",
        "hints": [
          "Pour passer du décimal au binaire, divisez par 2 successivement et lisez les restes **de bas en haut** ; en hexadécimal, les chiffres vont de 0 à F (F = 15).",
          "Pour revenir en décimal, chaque chiffre est multiplié par une puissance de la base : 1, 2, 4, 8, 16… en binaire, 1, 16, 256… en hexadécimal."
        ]
      }
    },
    {
      "title": "Complément à deux",
      "chapter": "Représentation des données et architecture",
      "difficulty": 2,
      "skills": [
        "Entiers relatifs en binaire"
      ],
      "template": {
        "code": "bits = 8\nn = randnz(-128, 127)\nsens = choice([\"vers\", \"depuis\"])\nb = twos(n, bits)",
        "statement": "{{ (\"Donner l'écriture en complément à deux sur 8 bits de l'entier \" + str(n) + \".\") if sens == \"vers\" else (\"Quel entier relatif est codé par \" + group(b) + \" en complément à deux sur 8 bits ?\") }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "b if sens == 'vers' else str(n)",
            "ignore_spaces": true
          }
        ],
        "solution": "{{ n }} s'écrit {{ group(b) }} en complément à deux sur 8 bits."
      }
    },
    {
      "title": "Expressions booléennes",
      "chapter": "Représentation des données et architecture",
      "difficulty": 1,
      "skills": [
        "Logique booléenne"
      ],
      "template": {
        "code": "a, b, c = coin(), coin(), coin()\nforme = choice([\"(a and not b) or c\", \"not (a or b) and c\", \"(a or b) and not (b and c)\", \"a != (b or c)\", \"not a or (b and c)\"])\nval = eval(forme, {\"a\": a, \"b\": b, \"c\": c})",
        "statement": "On a `a = {{ a }}`, `b = {{ b }}` et `c = {{ c }}`. Que vaut `{{ forme }}` ?",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "[('True', val), ('False', not val)]",
            "shuffle": false
          }
        ],
        "solution": "`{{ forme }}` vaut `{{ val }}`."
      }
    },
    {
      "title": "SQL : sélection avec condition",
      "chapter": "Bases de données",
      "difficulty": 2,
      "skills": [
        "SQL : SELECT ... WHERE"
      ],
      "template": {
        "code": "villes = sample(VILLES, 4)\neleves = [(i, choice(PRENOMS), randint(15, 19), choice(villes)) for i in range(1, randint(7, 10))]\nsetup = (\"CREATE TABLE Eleve(id INTEGER PRIMARY KEY, prenom TEXT, age INTEGER, ville TEXT);\\n\"\n         + sql_insert(\"Eleve\", eleves))\n\nage = randint(16, 18)\ncmp = choice([\">=\", \"<\", \"=\"])\nmots = {\">=\": \"au moins\", \"<\": \"strictement moins de\", \"=\": \"exactement\"}\nville = choice(villes)\navec_ville = coin()\nq_ref = f\"SELECT prenom FROM Eleve WHERE age {cmp} {age}\" + (f\" AND ville = '{ville}'\" if avec_ville else \"\")\nrequire(len(sql_run(setup, q_ref)) > 0)",
        "statement": "On dispose de la table **Eleve** :\n\n{{ sql_table(setup, 'Eleve') }}\n\nÉcrire une requête SQL qui donne le **prénom** des élèves ayant {{ mots[cmp] }} {{ age }} ans{{ (\" et habitant à \" + ville) if avec_ville else \"\" }}.",
        "fields": [
          {
            "type": "sql",
            "label": "Requête",
            "setup": "setup",
            "answer": "q_ref"
          }
        ],
        "solution": "```sql\n{{ q_ref }}\n```",
        "hints": [
          "On ne veut que la colonne `prenom` : `SELECT prenom FROM Eleve`, puis on filtre les lignes avec `WHERE`.",
          "Plusieurs conditions se combinent avec `AND` ; une chaîne de caractères s'écrit entre apostrophes : `'{{ ville }}'`."
        ]
      }
    },
    {
      "title": "SQL : agrégation et regroupement",
      "chapter": "Bases de données",
      "difficulty": 3,
      "skills": [
        "SQL : fonctions d'agrégation",
        "SQL : GROUP BY"
      ],
      "template": {
        "code": "villes = sample(VILLES, 4)\neleves = [(i, choice(PRENOMS), randint(15, 19), choice(villes)) for i in range(1, randint(7, 10))]\nsetup = (\"CREATE TABLE Eleve(id INTEGER PRIMARY KEY, prenom TEXT, age INTEGER, ville TEXT);\\n\"\n         + sql_insert(\"Eleve\", eleves))\n\nkind = choice([\"count_ville\", \"avg_age\", \"count_age\"])\nif kind == \"count_ville\":\n    enonce = \"le **nombre d'élèves par ville** (colonnes : ville, nombre)\"\n    q_ref = \"SELECT ville, COUNT(*) FROM Eleve GROUP BY ville\"\nelif kind == \"avg_age\":\n    enonce = \"l'**âge moyen** des élèves de chaque ville (colonnes : ville, âge moyen)\"\n    q_ref = \"SELECT ville, AVG(age) FROM Eleve GROUP BY ville\"\nelse:\n    a = randint(16, 18)\n    enonce = f\"le **nombre d'élèves** ayant plus de {a} ans (strictement)\"\n    q_ref = f\"SELECT COUNT(*) FROM Eleve WHERE age > {a}\"",
        "statement": "Table **Eleve** :\n\n{{ sql_table(setup, 'Eleve') }}\n\nÉcrire une requête SQL qui donne {{ enonce }}.",
        "fields": [
          {
            "type": "sql",
            "label": "Requête",
            "setup": "setup",
            "answer": "q_ref"
          }
        ],
        "solution": "```sql\n{{ q_ref }}\n```"
      }
    },
    {
      "title": "SQL : jointure",
      "chapter": "Bases de données",
      "difficulty": 3,
      "skills": [
        "SQL : jointures"
      ],
      "template": {
        "code": "auteurs = [(i, n) for i, n in enumerate(sample([\"Hugo\", \"Zola\", \"Sand\", \"Verne\", \"Duras\", \"Camus\", \"Colette\"], 4), 1)]\ntitres = [\"Les Misérables\", \"Germinal\", \"La Mare au diable\", \"Vingt mille lieues\", \"L'Amant\", \"L'Étranger\",\n          \"Chéri\", \"Notre-Dame\", \"Nana\", \"Indiana\", \"Le Tour du monde\", \"La Peste\"]\nlivres = [(i, t, choice(auteurs)[0], randint(1830, 1960)) for i, t in enumerate(sample(titres, randint(6, 9)), 1)]\nsetup = (\"CREATE TABLE Auteur(id INTEGER PRIMARY KEY, nom TEXT);\\n\"\n         \"CREATE TABLE Livre(id INTEGER PRIMARY KEY, titre TEXT, id_auteur INTEGER REFERENCES Auteur(id), annee INTEGER);\\n\"\n         + sql_insert(\"Auteur\", auteurs) + \"\\n\" + sql_insert(\"Livre\", livres))\nan = randint(1860, 1930)\nq_ref = f\"SELECT Livre.titre, Auteur.nom FROM Livre JOIN Auteur ON Livre.id_auteur = Auteur.id WHERE Livre.annee < {an}\"\nrequire(len(sql_run(setup, q_ref)) > 0)",
        "statement": "Schéma :\n\n{{ sql_schema(setup) }}\n\n{{ sql_table(setup, 'Auteur') }}\n\n{{ sql_table(setup, 'Livre') }}\n\nÉcrire une requête donnant le **titre** et le **nom de l'auteur** de chaque livre paru avant {{ an }} (strictement).",
        "fields": [
          {
            "type": "sql",
            "label": "Requête",
            "setup": "setup",
            "answer": "q_ref"
          }
        ],
        "solution": "```sql\n{{ q_ref }}\n```"
      }
    },
    {
      "title": "Vocabulaire des bases de données",
      "chapter": "Bases de données",
      "difficulty": 1,
      "skills": [
        "Modèle relationnel"
      ],
      "template": {
        "code": "defs = [\n    (\"clé primaire\", \"attribut (ou groupe d'attributs) qui identifie de façon unique chaque ligne d'une table\"),\n    (\"clé étrangère\", \"attribut qui fait référence à la clé primaire d'une autre table\"),\n    (\"schéma relationnel\", \"description des tables, de leurs attributs et de leurs clés\"),\n    (\"domaine\", \"ensemble des valeurs que peut prendre un attribut\"),\n    (\"attribut\", \"colonne d'une table, désignée par un nom\"),\n    (\"enregistrement\", \"ligne d'une table (n-uplet)\"),\n]\nterme, definition = choice(defs)",
        "statement": "Quel terme correspond à la définition suivante ?\n\n> {{ definition }}",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "[(t, t == terme) for t, _ in sample(defs, len(defs))]"
          }
        ],
        "solution": "Il s'agit d'un·e **{{ terme }}**."
      }
    },
    {
      "title": "Dictionnaires : accès et modification",
      "chapter": "Python : dictionnaires",
      "difficulty": 1,
      "skills": [
        "Dictionnaires : accès et modification",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice([\"stock\", \"notes\", \"age\", \"scores\", \"prix\"])\ncles = sample(FRUITS if nom in (\"stock\", \"prix\") else PRENOMS, 3)\nd = {c: randint(1, 20) for c in cles}\nc1, c2 = sample(cles, 2)\nnouvelle = choice([c for c in (FRUITS if nom in (\"stock\", \"prix\") else PRENOMS) if c not in cles])\nk = randint(2, 5)\nlignes = [f\"{nom} = {d!r}\",\n          f\"{nom}[{c1!r}] = {nom}[{c1!r}] + {k}\",\n          f\"{nom}[{nouvelle!r}] = {nom}[{c2!r}] * 2\",\n          f\"del {nom}[{c2!r}]\",\n          f\"print(len({nom}), {nom}[{c1!r}], {nom}[{nouvelle!r}])\"]\nsrc = \"\\n\".join(lignes)\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage",
            "answer": "out"
          }
        ],
        "solution": "Après les modifications, le dictionnaire vaut `{{ evaluate(src.rsplit(chr(10), 1)[0], nom) }}` : le programme affiche `{{ out }}`.",
        "hints": [
          "Réécrivez le dictionnaire après chaque ligne. `del` supprime la clé **et** sa valeur ; affecter une clé absente la crée.",
          "`len` compte le nombre de **clés** du dictionnaire."
        ]
      }
    },
    {
      "title": "Dictionnaires : parcours",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : parcours",
        "Boucle for"
      ],
      "template": {
        "code": "nom = choice([\"d\", \"stock\", \"inventaire\", \"compte\"])\nd = {c: randint(0, 15) for c in sample(FRUITS, randint(4, 5))}\nseuil = randint(4, 10)\nkind = choice([\"cles\", \"somme\", \"max\"])\nif kind == \"cles\":\n    src = f\"{nom} = {d!r}\\nfor cle in {nom}:\\n    if {nom}[cle] >= {seuil}:\\n        print(cle)\"\nelif kind == \"somme\":\n    src = f\"{nom} = {d!r}\\ntotal = 0\\nfor cle, valeur in {nom}.items():\\n    if valeur < {seuil}:\\n        total = total + valeur\\nprint(total)\"\nelse:\n    src = f\"{nom} = {d!r}\\nmeilleur = None\\nfor cle in {nom}:\\n    if meilleur is None or {nom}[cle] > {nom}[meilleur]:\\n        meilleur = cle\\nprint(meilleur)\"\nrequire(len(set(d.values())) == len(d))\nout = run(src)\nrequire(out != \"\")",
        "statement": "Qu'affiche ce programme ? (une valeur par ligne s'il y en a plusieurs)\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "out",
            "multiline": true
          }
        ],
        "solution": "Le parcours d'un dictionnaire se fait sur ses **clés**, dans l'ordre d'insertion ; `.items()` donne les couples (clé, valeur). Affichage :\n\n{{ code_block(out, 'text') }}",
        "hints": [
          "`for cle in {{ nom }}` parcourt les **clés** dans l'ordre où elles ont été insérées ; la valeur associée s'obtient avec `{{ nom }}[cle]`."
        ]
      }
    },
    {
      "title": "Écrire une fonction : compter avec un dictionnaire",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : construction",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname = choice([\"frequences\", \"compter\", \"occurrences\"])\nkind = choice([\"lettres\", \"mots\"])\ncases = []\nfor _ in range(5):\n    if kind == \"lettres\":\n        arg = randword(randint(3, 10), \"abcde\")\n        attendu = {}\n        for c in arg:\n            attendu[c] = attendu.get(c, 0) + 1\n    else:\n        arg = [choice(FRUITS[:4]) for _ in range(randint(0, 7))]\n        attendu = {}\n        for m in arg:\n            attendu[m] = attendu.get(m, 0) + 1\n    cases.append(((arg,), attendu))\nexemple = cases[0][0][0]",
        "statement": "Écrire une fonction `{{ fname }}({{ \"mot\" if kind == \"lettres\" else \"liste\" }})` qui renvoie un **dictionnaire** associant à chaque {{ \"lettre du mot\" if kind == \"lettres\" else \"élément de la liste\" }} son nombre d'apparitions.\n\nExemple : `{{ fname }}({{ repr(exemple) }})` renvoie `{{ cases[0][1] }}`.",
        "fields": [
          {
            "type": "code",
            "label": "",
            "forbid": [
              "Counter",
              "count"
            ],
            "starter": "def {{ fname }}({{ 'mot' if kind == 'lettres' else 'liste' }}):\n    ",
            "tests": "fn = student.get(fname)\ncheck(callable(fn), f'la fonction {fname} doit être définie')\nif callable(fn):\n    for (arg,), attendu in cases:\n        check_equal(fn(arg), attendu, f'{fname}({arg!r}) doit renvoyer {attendu}')"
          }
        ],
        "solution": "```python\ndef {{ fname }}(sequence):\n    d = {}\n    for e in sequence:\n        if e in d:\n            d[e] = d[e] + 1\n        else:\n            d[e] = 1\n    return d\n```"
      }
    },
    {
      "title": "Objets : qu'affiche ce programme ?",
      "chapter": "Programmation orientée objet",
      "difficulty": 2,
      "skills": [
        "POO : classes et attributs",
        "POO : méthodes",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "cls, attr = choice([(\"Compte\", \"solde\"), (\"Personnage\", \"vie\"), (\"Reservoir\", \"niveau\"), (\"Joueur\", \"score\")])\ndepart = randint(10, 50)\na, b = randint(2, 9), randint(2, 9)\nm1, m2 = {\"Compte\": (\"deposer\", \"retirer\"), \"Personnage\": (\"soigner\", \"blesser\"),\n          \"Reservoir\": (\"remplir\", \"vider\"), \"Joueur\": (\"gagner\", \"perdre\")}[cls]\no1, o2 = sample([\"x\", \"y\", \"p\", \"q\", \"obj\", \"u\", \"v\"], 2)\nsrc = dedent(f'''\nclass {cls}:\n    def __init__(self, {attr}):\n        self.{attr} = {attr}\n\n    def {m1}(self, n):\n        self.{attr} = self.{attr} + n\n\n    def {m2}(self, n):\n        if n <= self.{attr}:\n            self.{attr} = self.{attr} - n\n\n{o1} = {cls}({depart})\n{o2} = {o1}\n{o1}.{m1}({a})\n{o2}.{m2}({choice([b, depart + 100])})\nprint({o1}.{attr})\n''')\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Affichage",
            "answer": "int(out)"
          }
        ],
        "solution": "`{{ o2 }} = {{ o1 }}` ne crée pas de nouvel objet : les deux noms désignent **le même** objet. Le programme affiche **{{ out }}**.",
        "hints": [
          "Combien d'objets `{{ cls }}` sont créés ? Regardez combien de fois on écrit `{{ cls }}(...)`.",
          "`{{ o2 }} = {{ o1 }}` ne copie pas l'objet : `{{ o2 }}` et `{{ o1 }}` désignent le même objet, donc une modification via l'un se voit via l'autre."
        ]
      }
    },
    {
      "title": "Écrire une classe",
      "chapter": "Programmation orientée objet",
      "difficulty": 3,
      "skills": [
        "POO : écrire une classe",
        "POO : méthodes"
      ],
      "template": {
        "code": "cls = choice([\"Rectangle\", \"Compteur\", \"Temperature\"])\nk = randint(2, 5)\nif cls == \"Rectangle\":\n    consigne = (\"une classe `Rectangle` dont le constructeur prend `largeur` et `hauteur`, avec une méthode \"\n                \"`aire()` qui renvoie l'aire et une méthode `agrandir(k)` qui multiplie les deux dimensions par `k`.\")\n    tests = dedent('''\n    for (l, h) in dims:\n        r = Rectangle(l, h)\n        check_equal(r.aire(), l * h, f\"Rectangle({l}, {h}).aire() doit valoir {l * h}\")\n        r.agrandir(k)\n        check_equal(r.aire(), l * h * k * k, f\"après agrandir({k}), l'aire doit valoir {l * h * k * k}\")\n    ''')\n    ref = (\"class Rectangle:\\n    def __init__(self, largeur, hauteur):\\n        self.largeur = largeur\\n        self.hauteur = hauteur\\n\\n\"\n           \"    def aire(self):\\n        return self.largeur * self.hauteur\\n\\n\"\n           \"    def agrandir(self, k):\\n        self.largeur = self.largeur * k\\n        self.hauteur = self.hauteur * k\\n\")\nelif cls == \"Compteur\":\n    consigne = (f\"une classe `Compteur` dont le constructeur ne prend aucun paramètre (valeur initiale 0), avec une méthode \"\n                f\"`incrementer()` qui augmente la valeur de {k}, une méthode `valeur()` qui la renvoie et une méthode `raz()` qui la remet à 0.\")\n    tests = dedent('''\n    for (n, _) in dims:\n        c = Compteur()\n        check_equal(c.valeur(), 0, \"un nouveau compteur vaut 0\")\n        for _ in range(n):\n            c.incrementer()\n        check_equal(c.valeur(), n * k, f\"après {n} appels à incrementer(), valeur() doit renvoyer {n * k}\")\n        c.raz()\n        check_equal(c.valeur(), 0, \"après raz(), valeur() doit renvoyer 0\")\n    ''')\n    ref = (f\"class Compteur:\\n    def __init__(self):\\n        self.n = 0\\n\\n    def incrementer(self):\\n        self.n = self.n + {k}\\n\\n\"\n           \"    def valeur(self):\\n        return self.n\\n\\n    def raz(self):\\n        self.n = 0\\n\")\nelse:\n    consigne = (\"une classe `Temperature` dont le constructeur prend une température en degrés Celsius `celsius`, avec une méthode \"\n                \"`fahrenheit()` qui renvoie sa valeur en degrés Fahrenheit (F = C × 9 / 5 + 32) et une méthode `est_negative()` qui renvoie un booléen.\")\n    tests = dedent('''\n    for (c, _) in dims:\n        t = Temperature(c - 20)\n        check_equal(t.fahrenheit(), (c - 20) * 9 / 5 + 32, f\"Temperature({c - 20}).fahrenheit()\")\n        check_equal(t.est_negative(), c - 20 < 0, f\"Temperature({c - 20}).est_negative()\")\n    ''')\n    ref = (\"class Temperature:\\n    def __init__(self, celsius):\\n        self.celsius = celsius\\n\\n\"\n           \"    def fahrenheit(self):\\n        return self.celsius * 9 / 5 + 32\\n\\n\"\n           \"    def est_negative(self):\\n        return self.celsius < 0\\n\")\ndims = [(randint(1, 12), randint(1, 12)) for _ in range(4)]\ntests = \"check(\" + repr(cls) + \" in student, 'la classe \" + cls + \" doit être définie')\\nif \" + repr(cls) + \" in student:\\n\" + indent(tests.strip(), 4)",
        "statement": "Écrire {{ consigne }}",
        "fields": [
          {
            "type": "code",
            "label": "Votre classe",
            "tests": "exec(tests)",
            "reference": "{{ ref }}"
          }
        ],
        "solution": "```python\n{{ ref }}\n```"
      }
    }
  ]
}
```
