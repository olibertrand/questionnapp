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
Les métadonnées (identifiant, titre, chapitre, compétences, difficulté, classes) sont gérées à part,
dans la base. L'**identifiant** (`uid`, ex. `DICO-07`) est unique : c'est lui qui permet de reconnaître
une question lors d'un import (une question déjà présente n'est jamais réimportée). Une question créée
dans l'application sans identifiant reçoit `Q-` suivi de son numéro (`Q-0042`).

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
| `tests` | code Python supplémentaire ; y utiliser `check(cond, message)`, `check_equal(obtenu, attendu, message)` et `erreur(e)` (décrit une exception levée par le code de l'élève, avec sa ligne : « ZeroDivisionError: division by zero (ligne 4) »), ainsi que `rerun(variables)`, qui réexécute le code de l'élève avec d'autres variables fournies et renvoie ce qu'il affiche (pour vérifier qu'il utilise les données au lieu de recopier le résultat). Y sont visibles : les variables du générateur, les définitions de l'élève, `student` (son espace de noms) `student_output` (ce que son programme a affiché) et `student_code` (le code soumis). |
| `given` | expression donnant un dictionnaire `{nom: valeur}` de variables **déjà définies** pour le code de l'élève (ex. `{"membres": membres}`) : l'élève écrit seulement les instructions qui les utilisent |
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
- Pour faire **écrire une instruction** qui utilise des données déjà définies (« écrire
  l'instruction qui affiche la ville de Laure »), fournir les données avec `given`
  (`{"membres": membres}`), comparer `student_output` au résultat attendu, puis appeler
  `rerun({nom: autres_donnees})` pour vérifier que l'élève lit bien les données au lieu de
  recopier la valeur (voir les exemples « écrire l'instruction d'affichage »).
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
- `uid` : identifiant unique de la question, en majuscules, de la forme `PREFIXE-NN` (par exemple
  `DICO-21` pour une question sur les dictionnaires). Continuer la numérotation du référentiel ou du
  fichier de banque existant ; pour un nouveau thème, choisir un préfixe court (`POO`, `REC`…).
- `title` : court et unique (« Dictionnaires : parcours »).

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

Le fichier à produire a exactement cette structure (`format`, `version`, `title` et `description` de la banque, puis la liste `questions`). Chaque question : `title`, `chapter`, `difficulty` (1 facile, 2 moyen, 3 difficile), `skills` (liste), `template`. Voici les 42 questions de la banque fournie avec l'application, toutes testées : elles montrent les bons usages de chaque type de champ.

```json
{
  "format": "questionnapp/questions",
  "version": 1,
  "title": "Exemples",
  "questions": [
    {
      "uid": "ALGO-01",
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
      "uid": "ALGO-02",
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
      "uid": "ALGO-03",
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
      "uid": "ALGO-04",
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
      "uid": "BDD-01",
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
      "uid": "BDD-02",
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
      "uid": "BDD-03",
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
      "uid": "BDD-04",
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
      "uid": "POO-01",
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
      "uid": "POO-02",
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
    },
    {
      "uid": "BASES-01",
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
      "uid": "BASES-02",
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
      "uid": "BASES-03",
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
      "uid": "BASES-04",
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
      "uid": "BASES-05",
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
      "uid": "DICO-01",
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
      "uid": "DICO-02",
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
      "uid": "DICO-03",
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
      "uid": "DICO-04",
      "title": "keys(), values() et items() : que vaut l'expression ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 1,
      "skills": [
        "Dictionnaires : keys, values, items"
      ],
      "template": {
        "code": "nom = choice([\"d\", \"stock\", \"notes\", \"prix\", \"ages\"])\npool = FRUITS if nom in (\"stock\", \"prix\") else PRENOMS\ncles = sample(pool, randint(3, 4))\nd = {c: randint(1, 20) for c in cles}\nrequire(len(set(d.values())) == len(d))\nk = choice(cles)\nv = choice(list(d.values()))\ni = randint(0, len(d) - 1)\nexpr = choice([\n    f\"list({nom}.keys())\", f\"list({nom}.values())\", f\"list({nom}.items())[{i}]\",\n    f\"sum({nom}.values())\", f\"max({nom}.values())\", f\"{k!r} in {nom}\", f\"{v} in {nom}\",\n    f\"{v} in {nom}.values()\", f\"{k!r} in {nom}.values()\", f\"len({nom}.items())\",\n    f\"list({nom}.values())[{i}]\", f\"list({nom}.keys())[-1]\",\n])\nres = eval(expr, {nom: d})\nrep = repr(res)",
        "statement": "On définit :\n\n{{ code_block(nom + \" = \" + repr(d)) }}\n\nQue vaut l'expression `{{ expr }}` ? Écrire la valeur comme Python l'afficherait.",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "[rep, rep.replace(\"'\", '\"')]",
            "ignore_spaces": true
          }
        ],
        "solution": "`{{ expr }}` vaut `{{ rep }}`.\n\n- `.keys()` : les clés, `.values()` : les valeurs, `.items()` : les couples `(clé, valeur)`, dans l'ordre d'insertion.\n- `x in {{ nom }}` teste si `x` est une **clé** ; pour chercher parmi les valeurs, il faut `x in {{ nom }}.values()`.",
        "hints": [
          "`.keys()` donne les clés, `.values()` les valeurs et `.items()` les couples `(clé, valeur)`, toujours dans l'ordre d'insertion. `list(...)` les met dans une liste.",
          "Attention : `x in {{ nom }}` teste si `x` est une **clé** du dictionnaire, pas une valeur."
        ]
      }
    },
    {
      "uid": "DICO-05",
      "title": "Parcourir avec .items()",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : keys, values, items",
        "Dictionnaires : parcours"
      ],
      "template": {
        "code": "nom = choice([\"stock\", \"inventaire\", \"d\", \"panier\"])\nd = {c: randint(0, 15) for c in sample(FRUITS, randint(4, 5))}\ns = randint(4, 10)\nkv = choice([(\"cle\", \"valeur\"), (\"fruit\", \"quantite\"), (\"k\", \"v\"), (\"nom\", \"nb\")])\nk, v = kv\nkind = choice([\"filtre\", \"rupture\", \"compte\"])\nif kind == \"filtre\":\n    src = f\"{nom} = {d!r}\\nfor {k}, {v} in {nom}.items():\\n    if {v} > {s}:\\n        print({k}, {v})\"\nelif kind == \"rupture\":\n    src = (f\"{nom} = {d!r}\\nfor {k}, {v} in {nom}.items():\\n    if {v} < {s}:\\n        print({k}, 'à commander')\\n\"\n           f\"    else:\\n        print({k}, {v})\")\nelse:\n    src = (f\"{nom} = {d!r}\\nn = 0\\nfor {k}, {v} in {nom}.items():\\n    if {v} < {s} and len({k}) > 5:\\n\"\n           f\"        n = n + 1\\nprint(n)\")\nout = run(src)\nrequire(out.strip() != \"\")\nif kind == \"filtre\":\n    require(0 < len(out.split(\"\\n\")) < len(d))",
        "statement": "Qu'affiche ce programme ? (une ligne par `print`)\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "out",
            "multiline": true
          }
        ],
        "solution": "À chaque tour, `{{ k }}` reçoit une clé et `{{ v }}` la valeur associée. Le programme affiche :\n\n{{ code_block(out, 'text') }}",
        "hints": [
          "À chaque tour de boucle, `{{ k }}` prend une clé et `{{ v }}` la valeur associée, dans l'ordre du dictionnaire : écrivez les couples un par un.",
          "Pour chaque couple, évaluez la condition du `if` avant d'écrire ce que produit le `print`."
        ]
      }
    },
    {
      "uid": "DICO-06",
      "title": "Quelle boucle convient ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : keys, values, items",
        "Dictionnaires : parcours"
      ],
      "template": {
        "code": "d = {c: randint(1, 9) for c in sample(FRUITS, 3)}\nrequire(len(set(d.values())) == 3)\nbuts = {\n    \"les valeurs du dictionnaire, une par ligne\": \"\\n\".join(str(x) for x in d.values()),\n    \"les clés du dictionnaire, une par ligne\": \"\\n\".join(d),\n    \"chaque clé suivie de sa valeur (par exemple `\" + list(d)[0] + \" \" + str(d[list(d)[0]]) + \"`), une par ligne\":\n        \"\\n\".join(f\"{a} {b}\" for a, b in d.items()),\n}\nbut = choice(list(buts))\nattendu = buts[but]\ncandidats = [\n    \"for x in d:\\n    print(x)\",\n    \"for x in d.keys():\\n    print(x)\",\n    \"for x in d.values():\\n    print(x)\",\n    \"for x in d:\\n    print(d[x])\",\n    \"for x in d.values():\\n    print(d[x])\",\n    \"for k, v in d.items():\\n    print(k, v)\",\n    \"for k, v in d:\\n    print(k, v)\",\n    \"for x in d.items():\\n    print(x)\",\n    \"for x in d:\\n    print(x, d[x])\",\n]\ndef sortie(code):\n    try:\n        return run(\"d = \" + repr(d) + \"\\n\" + code)\n    except Exception:\n        return None\nbons = [c for c in candidats if sortie(c) == attendu]\nmauvais = [c for c in candidats if sortie(c) != attendu]\nchoisis = sample(bons, min(2, len(bons))) + sample(mauvais, 4 - min(2, len(bons)))\noptions = [(\"```python\\n\" + c + \"\\n```\", c in bons) for c in shuffled(choisis)]\ndef explication(c):\n    s = sortie(c)\n    if s is None:\n        return \"provoque une erreur (\" + run_error(\"d = \" + repr(d) + \"\\n\" + c) + \")\"\n    return \"affiche \" + \" / \".join(s.split(\"\\n\"))\nexpl = \"\\n\".join(\"- `\" + c.replace(\"\\n\", \" \").replace(\"    \", \"\") + \"` \" + explication(c) for c, _ in [(o[0][10:-4], 0) for o in options])",
        "statement": "On dispose du dictionnaire `d = {{ repr(d) }}`.\n\nQuels programmes affichent **{{ but }}** ? (plusieurs réponses possibles)",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "options",
            "multiple": true,
            "shuffle": false
          }
        ],
        "solution": "{{ expl }}\n\nParcourir `d` ou `d.keys()` donne les clés ; `d.values()` donne les valeurs (sans les clés) ; `d.items()` donne les couples.",
        "hints": [
          "Pour chaque programme, demandez-vous ce que contient `x` (ou `k` et `v`) à chaque tour : une clé, une valeur ou un couple ?",
          "`d[x]` n'a de sens que si `x` est une **clé** ; et `for k, v in d:` essaie de découper chaque clé en deux."
        ]
      }
    },
    {
      "uid": "DICO-07",
      "title": "Recherche d'un maximum ou d'un minimum : qu'affiche ce programme ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : recherche de max/min",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice([\"temperatures\", \"scores\", \"soldes\", \"ecarts\"])\nkind = choice([\"max_cle\", \"min_val\", \"max_init0\", \"min_cle\"])\nnegatif = kind == \"max_init0\" and coin(0.7)\ncles = sample(VILLES if nom == \"temperatures\" else PRENOMS, randint(4, 5))\nvals = sample(range(-25, -1), len(cles)) if negatif else sample(range(-9, 30), len(cles))\nd = dict(zip(cles, vals))\nif kind == \"max_cle\":\n    corps = f\"meilleur = None\\nfor k in {nom}:\\n    if meilleur is None or {nom}[k] > {nom}[meilleur]:\\n        meilleur = k\\nprint(meilleur)\"\nelif kind == \"min_cle\":\n    premier = list(d)[0]\n    corps = f\"m = {premier!r}\\nfor k, v in {nom}.items():\\n    if v < {nom}[m]:\\n        m = k\\nprint(m, {nom}[m])\"\nelif kind == \"min_val\":\n    corps = f\"m = None\\nfor v in {nom}.values():\\n    if m is None or v < m:\\n        m = v\\nprint(m)\"\nelse:\n    corps = f\"m = 0\\nfor v in {nom}.values():\\n    if v > m:\\n        m = v\\nprint(m)\"\nsrc = f\"{nom} = {d!r}\\n\" + corps\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "out"
          }
        ],
        "solution": "Le programme affiche `{{ out }}`.\n{{ \"Attention : `m` démarre à 0, et comme toutes les valeurs sont négatives, aucune n'est plus grande que 0 : le programme affiche 0 au lieu du vrai maximum (\" + str(max(d.values())) + \"). Il faut initialiser avec une valeur du dictionnaire (ou `None`).\" if kind == \"max_init0\" and negatif else \"\" }}",
        "hints": [
          "Faites un tableau avec la valeur de la variable qui garde le meilleur (`m` ou `meilleur`) après chaque tour de boucle.",
          "Regardez bien la valeur de départ de cette variable et le sens de la comparaison (`<` ou `>`)."
        ]
      }
    },
    {
      "uid": "DICO-08",
      "title": "Écrire une fonction : clé de la plus grande ou de la plus petite valeur",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : recherche de max/min",
        "Écrire une fonction"
      ],
      "template": {
        "code": "kind = choice([\"max\", \"min\"])\nfname = choice([\"cle_du_max\", \"meilleur\", \"le_plus_grand\"] if kind == \"max\" else [\"cle_du_min\", \"moins_cher\", \"le_plus_petit\"])\nparams = \"d\"\ncases = []\nfor n in range(6):\n    cles = sample(PRENOMS + FRUITS, randint(3, 5) if n == 0 else randint(1, 6))\n    vals = sample(range(-30, 40), len(cles))\n    dd = dict(zip(cles, vals))\n    cases.append(((dd,), (max if kind == \"max\" else min)(dd, key=dd.get)))\ncases.append((({\"a\": -5, \"b\": -2, \"c\": -9},), \"b\" if kind == \"max\" else \"c\"))\nsigne = \">\" if kind == \"max\" else \"<\"\nref = (f\"def {fname}(d):\\n    meilleure = None\\n    for cle in d:\\n\"\n       f\"        if meilleure is None or d[cle] {signe} d[meilleure]:\\n            meilleure = cle\\n    return meilleure\\n\")\nexemple = cases[0][0][0]",
        "statement": "Écrire une fonction `{{ fname }}(d)` qui reçoit un dictionnaire **non vide** dont les valeurs sont des nombres tous différents, et qui renvoie la **clé** associée à la plus {{ \"grande\" if kind == \"max\" else \"petite\" }} valeur.\n\nExemple : `{{ fname }}({{ repr(exemple) }})` renvoie `{{ repr(cases[0][1]) }}`.\n\nLes fonctions `max`, `min`, `sorted` et la méthode `sort` sont interdites.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "max",
              "min",
              "sorted",
              "sort"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn garde la **clé** de la meilleure valeur vue jusqu'ici, et on compare avec `d[meilleure]`. Démarrer avec `None` (ou avec la première clé) évite le piège d'un maximum initialisé à 0 alors que les valeurs peuvent être négatives.",
        "hints": [
          "Parcourez les clés en gardant dans une variable la **clé** de la meilleure valeur rencontrée jusqu'ici ; comparez `d[cle]` avec `d[meilleure]`.",
          "N'initialisez pas avec 0 : les valeurs peuvent toutes être négatives. Partez de `None` (ou de la première clé) — un des tests utilise des valeurs négatives."
        ]
      }
    },
    {
      "uid": "DICO-09",
      "title": "Total : parcourir les clés ou les valeurs ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : calcul cumulatif",
        "Dictionnaires : keys, values, items"
      ],
      "template": {
        "code": "nom = choice([\"stock\", \"panier\", \"d\", \"inventaire\"])\nd = {c: randint(1, 12) for c in sample(FRUITS, randint(4, 5))}\nf, qv = choice([(\"f\", \"q\"), (\"cle\", \"valeur\"), (\"fruit\", \"n\")])\nsrc_a = f\"total = 0\\nfor {f} in {nom}:\\n    total = total + {nom}[{f}]\\nprint(total)\"\nsrc_b = f\"total = 0\\nfor {qv} in {nom}.values():\\n    total = total + {qv}\\nprint(total)\"\na = int(run(f\"{nom} = {d!r}\\n\" + src_a))\nb = int(run(f\"{nom} = {d!r}\\n\" + src_b))\nsur_cle = coin()\nif sur_cle:\n    lettre = choice(sorted({c[0] for c in d}))\n    condition = f\"les fruits dont le nom commence par « {lettre} »\"\nelse:\n    seuil = randint(4, 8)\n    condition = f\"les quantités supérieures ou égales à {seuil}\"\noptions = [(\"Le parcours des clés (`for \" + f + \" in \" + nom + \":`)\", sur_cle),\n           (\"Le parcours des valeurs (`for \" + qv + \" in \" + nom + \".values():`)\", False),\n           (\"Les deux conviennent\", not sur_cle)]",
        "statement": "On dispose de `{{ nom }} = {{ repr(d) }}` et de deux programmes :\n\n**Programme A**\n\n{{ code_block(src_a) }}\n\n**Programme B**\n\n{{ code_block(src_b) }}",
        "fields": [
          {
            "type": "number",
            "label": "Affichage du programme A",
            "answer": "a"
          },
          {
            "type": "number",
            "label": "Affichage du programme B",
            "answer": "b"
          },
          {
            "type": "choice",
            "label": "On veut maintenant additionner seulement **{{ condition }}**. Quel parcours permet de le faire ?",
            "options": "options",
            "shuffle": false
          }
        ],
        "solution": "Les deux programmes calculent la même somme ({{ a }}) : A parcourt les clés et va chercher chaque valeur avec `{{ nom }}[{{ f }}]`, B parcourt directement les valeurs.\n\n{{ \"Pour une condition sur le **nom** du fruit, il faut connaître la clé : seul le parcours des clés (ou de `.items()`) convient ; dans B, on n'a que les nombres.\" if sur_cle else \"La condition ne porte que sur les **valeurs** : les deux parcours conviennent (dans A, on teste `\" + nom + \"[\" + f + \"]`, dans B directement `\" + qv + \"`).\" }}",
        "hints": [
          "A et B additionnent-ils les mêmes nombres ? Écrivez, tour après tour, ce qui est ajouté à `total` dans chacun.",
          "Avec `.values()`, la boucle ne voit que les nombres : on n'a plus accès aux clés. La condition demandée porte-t-elle sur une clé ou sur une valeur ?"
        ]
      }
    },
    {
      "uid": "DICO-10",
      "title": "Écrire une fonction : calcul cumulatif sur un dictionnaire",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : calcul cumulatif",
        "Écrire une fonction"
      ],
      "template": {
        "code": "kind = choice([\"total\", \"moyenne\", \"compter\", \"total_si\"])\ndef dico(n):\n    return {c: randint(0, 20) for c in sample(FRUITS + PRENOMS, n)}\ncases = []\nif kind == \"total\":\n    fname, params = choice([\"total\", \"somme_valeurs\", \"quantite_totale\"]), \"d\"\n    consigne = \"renvoie la **somme** de toutes les valeurs du dictionnaire `d` (0 si `d` est vide)\"\n    for n in [4, 0, 1, 3, 5]:\n        dd = dico(n)\n        cases.append(((dd,), sum(dd.values())))\n    ref = f\"def {fname}(d):\\n    total = 0\\n    for v in d.values():\\n        total = total + v\\n    return total\\n\"\n    forbid = [\"sum\"]\nelif kind == \"moyenne\":\n    fname, params = choice([\"moyenne\", \"moyenne_valeurs\"]), \"d\"\n    consigne = \"renvoie la **moyenne** des valeurs du dictionnaire `d`, supposé non vide\"\n    for n in [4, 1, 3, 5, 2]:\n        dd = dico(n)\n        cases.append(((dd,), sum(dd.values()) / len(dd)))\n    ref = f\"def {fname}(d):\\n    total = 0\\n    for v in d.values():\\n        total = total + v\\n    return total / len(d)\\n\"\n    forbid = [\"sum\"]\nelif kind == \"compter\":\n    fname, params = choice([\"compter\", \"nb_au_dessus\", \"combien\"]), \"d, seuil\"\n    consigne = \"renvoie le **nombre de clés** dont la valeur est supérieure ou égale à `seuil`\"\n    for n in [5, 0, 3, 4, 6]:\n        dd = dico(n)\n        s = randint(5, 15)\n        cases.append(((dd, s), sum(1 for v in dd.values() if v >= s)))\n    ref = f\"def {fname}(d, seuil):\\n    n = 0\\n    for v in d.values():\\n        if v >= seuil:\\n            n = n + 1\\n    return n\\n\"\n    forbid = [\"sum\", \"count\"]\nelse:\n    fname, params = choice([\"total_si\", \"somme_lettre\"]), \"d, lettre\"\n    consigne = \"renvoie la somme des valeurs associées aux clés qui **commencent par** `lettre` (une chaîne d'un caractère)\"\n    for n in [5, 0, 4, 6, 3]:\n        dd = dico(n)\n        l = choice([c[0] for c in dd] or [\"a\"])\n        cases.append(((dd, l), sum(v for c, v in dd.items() if c[0] == l)))\n    ref = f\"def {fname}(d, lettre):\\n    total = 0\\n    for cle, v in d.items():\\n        if cle[0] == lettre:\\n            total = total + v\\n    return total\\n\"\n    forbid = [\"sum\"]\nexemple, attendu = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui {{ consigne }}.\n\nExemple : `{{ fname }}({{ \", \".join(repr(x) for x in exemple) }})` renvoie `{{ repr(attendu) }}`.\n\nLa fonction `sum` est interdite : utilisez une variable qui accumule le résultat.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "sum",
              "count"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}",
        "hints": [
          "Utilisez une variable (un « accumulateur ») initialisée **avant** la boucle, puis mise à jour à chaque tour.",
          "{{ 'La condition porte sur les clés : parcourez `d.items()` (ou les clés) pour avoir la clé et la valeur.' if kind == 'total_si' else 'Ici, seules les valeurs comptent : `for v in d.values():` suffit.' }} Pensez au cas du dictionnaire vide."
        ]
      }
    },
    {
      "uid": "DICO-11",
      "title": "Écrire une fonction : prix d'un panier",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : calcul cumulatif",
        "Dictionnaires : accès et modification",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname, params = choice([\"total_panier\", \"prix_panier\", \"a_payer\"]), \"panier, prix\"\ncases = []\nfor n in [3, 0, 1, 4, 5]:\n    tarif = {c: randint(1, 9) for c in sample(FRUITS, 7)}\n    panier = {c: randint(1, 5) for c in sample(sorted(tarif), n)}\n    cases.append(((panier, tarif), sum(q * tarif[c] for c, q in panier.items())))\nref = (f\"def {fname}(panier, prix):\\n    total = 0\\n    for article, quantite in panier.items():\\n\"\n       f\"        total = total + quantite * prix[article]\\n    return total\\n\")\n(ex_panier, ex_prix), ex_total = cases[0]",
        "statement": "Un panier est un dictionnaire qui associe à chaque article la **quantité** achetée ; les tarifs sont dans un dictionnaire `prix` qui associe à chaque article son **prix unitaire** (il contient tous les articles du panier, et d'autres).\n\nÉcrire une fonction `{{ fname }}(panier, prix)` qui renvoie le montant total à payer.\n\nExemple : avec `panier = {{ repr(ex_panier) }}` et `prix = {{ repr(ex_prix) }}`, la fonction renvoie `{{ ex_total }}`.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}"
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn parcourt le **panier** (pas les prix : on n'achète pas tout) et on va chercher le prix de chaque article dans l'autre dictionnaire.",
        "hints": [
          "Quel dictionnaire faut-il parcourir : celui des prix ou celui du panier ? On ne paie que ce qui est dans le panier.",
          "Pour chaque article du panier, le montant est `quantite * prix[article]` ; additionnez ces montants dans une variable."
        ]
      }
    },
    {
      "uid": "DICO-12",
      "title": "Dictionnaire de dictionnaires : qu'affiche ce programme ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 1,
      "skills": [
        "Données imbriquées : dictionnaire de dictionnaires",
        "Dictionnaires : accès et modification"
      ],
      "template": {
        "code": "def joli(d, nom):\n    lignes = [f\"    {k!r}: {v!r},\" for k, v in d.items()]\n    return nom + \" = {\\n\" + \"\\n\".join(lignes) + \"\\n}\"\n\nnom = choice([\"eleves\", \"fiches\", \"membres\"])\np1, p2, p3 = sample(PRENOMS, 3)\nd = {p: {\"age\": randint(15, 18), \"ville\": choice(VILLES)} for p in (p1, p2, p3)}\nnv = choice([v for v in VILLES if v != d[p2][\"ville\"]])\nk = randint(1, 3)\nlignes = [joli(d, nom),\n          f\"{nom}[{p1!r}]['age'] = {nom}[{p1!r}]['age'] + {k}\",\n          f\"{nom}[{p2!r}]['ville'] = {nv!r}\",\n          f\"{nom}[{p3!r}]['classe'] = '1G{randint(1, 9)}'\",\n          f\"print({nom}[{p1!r}]['age'], {nom}[{p2!r}]['ville'], len({nom}[{p3!r}]), len({nom}))\"]\nsrc = \"\\n\".join(lignes)\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage (valeurs séparées par un espace, comme `print`)",
            "answer": "out"
          }
        ],
        "solution": "`{{ nom }}[{{ repr(p1) }}]` est lui-même un dictionnaire ; `{{ nom }}[{{ repr(p1) }}]['age']` va chercher la clé `'age'` dans ce dictionnaire. Le programme affiche `{{ out }}`.",
        "hints": [
          "`{{ nom }}[{{ repr(p1) }}]` est un dictionnaire `{'age': ..., 'ville': ...}` : lisez `{{ nom }}[{{ repr(p1) }}]['age']` de gauche à droite.",
          "`len` d'un dictionnaire compte ses **clés** : ajouter la clé `'classe'` à la fiche de {{ p3 }} en fait une de plus ; `len({{ nom }})` compte les élèves."
        ]
      }
    },
    {
      "uid": "DICO-13",
      "title": "Dictionnaire de listes : qu'affiche ce programme ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 1,
      "skills": [
        "Données imbriquées : dictionnaire de listes",
        "Listes : indices et tranches"
      ],
      "template": {
        "code": "def joli(d, nom):\n    lignes = [f\"    {k!r}: {v!r},\" for k, v in d.items()]\n    return nom + \" = {\\n\" + \"\\n\".join(lignes) + \"\\n}\"\n\nnom = choice([\"notes\", \"resultats\", \"releves\"])\np1, p2, p3 = sample(PRENOMS, 3)\nd = {p: randlist(randint(2, 4), 5, 20) for p in (p1, p2, p3)}\nx = randint(5, 20)\nlignes = [joli(d, nom),\n          f\"{nom}[{p1!r}].append({x})\",\n          f\"{nom}[{p2!r}][0] = {nom}[{p2!r}][-1]\",\n          f\"print(len({nom}[{p1!r}]), {nom}[{p2!r}][0], sum({nom}[{p3!r}]), len({nom}))\"]\nsrc = \"\\n\".join(lignes)\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage (valeurs séparées par un espace, comme `print`)",
            "answer": "out"
          }
        ],
        "solution": "Chaque valeur est une **liste** : `{{ nom }}[{{ repr(p1) }}].append({{ x }})` modifie la liste de {{ p1 }} ; `{{ nom }}[{{ repr(p2) }}][-1]` est le dernier élément de la liste de {{ p2 }}. Le programme affiche `{{ out }}`.",
        "hints": [
          "`{{ nom }}[{{ repr(p1) }}]` est une liste : on peut lui appliquer tout ce qu'on fait sur une liste (`append`, indices, `len`, `sum`).",
          "`len({{ nom }}[...])` compte les éléments d'une liste, alors que `len({{ nom }})` compte les **clés** du dictionnaire."
        ]
      }
    },
    {
      "uid": "DICO-14",
      "title": "Liste de dictionnaires : qu'affiche ce programme ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : liste de dictionnaires",
        "Boucle for"
      ],
      "template": {
        "code": "def joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nnom = choice([\"films\", \"livres\", \"series\"])\ntitres = [\"Horizon\", \"La Forêt\", \"Nuit d'été\", \"Le Code\", \"Les Étoiles\", \"Mars\", \"L'Île\", \"Le Phare\", \"Orages\", \"Minuit\"]\nL = [{\"titre\": t, \"annee\": randint(1990, 2024), \"note\": n} for t, n in zip(sample(titres, 4), sample(range(8, 20), 4))]\nkind = choice([\"filtre\", \"meilleur\", \"moyenne\"])\ns = randint(11, 16)\na = randint(2000, 2015)\nif kind == \"filtre\":\n    corps = f\"for f in {nom}:\\n    if f['note'] >= {s} and f['annee'] > {a}:\\n        print(f['titre'])\"\nelif kind == \"meilleur\":\n    corps = f\"m = {nom}[0]\\nfor f in {nom}:\\n    if f['note'] > m['note']:\\n        m = f\\nprint(m['titre'], m['annee'])\"\nelse:\n    corps = f\"total = 0\\nfor f in {nom}:\\n    total = total + f['note']\\nprint(total / len({nom}))\"\nsrc = joli_liste(L, nom) + \"\\n\" + corps\nout = run(src)\nrequire(out.strip() != \"\")",
        "statement": "Qu'affiche ce programme ? (une ligne par `print`)\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "",
            "answer": "out",
            "multiline": true
          }
        ],
        "solution": "À chaque tour, `f` est **un dictionnaire** (une fiche) ; `f['note']` est sa note. Le programme affiche :\n\n{{ code_block(out, 'text') }}",
        "hints": [
          "`{{ nom }}` est une liste : la boucle `for f in {{ nom }}` donne successivement chaque fiche, c'est-à-dire un dictionnaire.",
          "Examinez les fiches une par une : notez `f['note']`{{ \" et `f['annee']`\" if kind == 'filtre' else '' }} puis appliquez le test du programme."
        ]
      }
    },
    {
      "uid": "DICO-15",
      "title": "Données imbriquées : quelle expression ?",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : dictionnaire de dictionnaires",
        "Données imbriquées : dictionnaire de listes",
        "Données imbriquées : liste de dictionnaires"
      ],
      "template": {
        "code": "def joli(d, nom):\n    lignes = [f\"    {k!r}: {v!r},\" for k, v in d.items()]\n    return nom + \" = {\\n\" + \"\\n\".join(lignes) + \"\\n}\"\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nkind = choice([\"dd\", \"dl\", \"ld\"])\nif kind == \"dd\":\n    nom = \"eleves\"\n    p = sample(PRENOMS, 3)\n    data = {x: {\"age\": randint(15, 18), \"ville\": choice(VILLES)} for x in p}\n    cible = choice(p)\n    champ = choice([\"age\", \"ville\"])\n    but = f\"{'l’âge' if champ == 'age' else 'la ville'} de {cible}\"\n    candidats = [f\"{nom}[{cible!r}][{champ!r}]\", f\"{nom}[{champ!r}][{cible!r}]\", f\"{nom}[{cible!r}].{champ}\",\n                 f\"{nom}[{cible!r}, {champ!r}]\", f\"{nom}[{cible!r}]\", f\"{nom}[{champ}][{cible!r}]\"]\n    attendu = data[cible][champ]\nelif kind == \"dl\":\n    nom = \"notes\"\n    p = sample(PRENOMS, 3)\n    data = {x: sample(range(5, 20), randint(3, 4)) for x in p}\n    cible = choice(p)\n    pos = choice([\"première\", \"dernière\", \"deuxième\"])\n    idx = {\"première\": \"0\", \"dernière\": \"-1\", \"deuxième\": \"1\"}[pos]\n    but = f\"la {pos} note de {cible}\"\n    candidats = [f\"{nom}[{cible!r}][{idx}]\", f\"{nom}[{idx}][{cible!r}]\", f\"{nom}[{cible!r}][{int(idx) + 1}]\",\n                 f\"{nom}[{cible!r}]\", f\"{nom}.{cible}[{idx}]\", f\"{nom}[{cible}][{idx}]\"]\n    attendu = data[cible][int(idx)]\nelse:\n    nom = \"films\"\n    titres = sample([\"Horizon\", \"Mars\", \"Le Code\", \"Orages\", \"Minuit\", \"Le Phare\"], 3)\n    data = [{\"titre\": t, \"note\": n} for t, n in zip(titres, sample(range(8, 20), 3))]\n    i = randint(0, 2)\n    rang = [\"premier\", \"deuxième\", \"troisième\"][i]\n    champ = choice([\"titre\", \"note\"])\n    but = f\"{'le titre' if champ == 'titre' else 'la note'} du {rang} film\"\n    candidats = [f\"{nom}[{i}][{champ!r}]\", f\"{nom}[{champ!r}][{i}]\", f\"{nom}[{i + 1}][{champ!r}]\",\n                 f\"{nom}[{i}].{champ}\", f\"{nom}[{i}]\", f\"{nom}[{i}][{champ}]\"]\n    attendu = data[i][champ]\ndef donne(e):\n    try:\n        return eval(e, {nom: data}) == attendu\n    except Exception:\n        return False\nbons = [c for c in candidats if donne(c)]\nrequire(len(bons) == 1)\nchoisis = bons + sample([c for c in candidats if c not in bons], 3)\noptions = [(\"`\" + c + \"`\", c in bons) for c in choisis]\ndef effet(e):\n    try:\n        return \"vaut `\" + repr(eval(e, {nom: data})) + \"`\"\n    except Exception as ex:\n        return \"provoque une erreur (`\" + type(ex).__name__ + \"`)\"\nexpl = \"\\n\".join(\"- `\" + c + \"` \" + effet(c) for c in choisis)",
        "statement": "On dispose de :\n\n{{ code_block(joli_liste(data, nom) if kind == \"ld\" else joli(data, nom)) }}\n\nQuelle expression donne **{{ but }}** ?",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "options"
          }
        ],
        "solution": "{{ expl }}\n\nOn lit de l'extérieur vers l'intérieur : d'abord l'élément de `{{ nom }}` (par sa clé ou son indice), puis dans cet élément.",
        "hints": [
          "Commencez par l'extérieur : `{{ nom }}` est {{ 'un dictionnaire' if kind != 'ld' else 'une liste' }}. Que faut-il écrire entre les premiers crochets ?",
          "Les clés d'un dictionnaire qui sont des chaînes s'écrivent entre guillemets ; la notation `x.nom` ne marche pas pour un dictionnaire."
        ]
      }
    },
    {
      "uid": "DICO-16",
      "title": "Écrire une fonction : parcourir une liste de dictionnaires",
      "chapter": "Python : dictionnaires",
      "difficulty": 3,
      "skills": [
        "Données imbriquées : liste de dictionnaires",
        "Écrire une fonction"
      ],
      "template": {
        "code": "kind = choice([\"titres\", \"moyenne\", \"meilleur\"])\ntitres = [\"Horizon\", \"La Forêt\", \"Le Code\", \"Mars\", \"Le Phare\", \"Orages\", \"Minuit\", \"Les Étoiles\"]\ndef films(n):\n    return [{\"titre\": t, \"annee\": randint(1990, 2024), \"note\": note}\n            for t, note in zip(sample(titres, n), sample(range(5, 20), n))]\ncases = []\nif kind == \"titres\":\n    fname, params = choice([\"titres_recents\", \"films_apres\"]), \"films, annee\"\n    consigne = \"renvoie la **liste des titres** des films sortis strictement après `annee`, dans l'ordre de la liste\"\n    for n in [4, 0, 5, 3, 6]:\n        L = films(n)\n        a = randint(1995, 2020)\n        cases.append(((L, a), [f[\"titre\"] for f in L if f[\"annee\"] > a]))\n    ref = f\"def {fname}(films, annee):\\n    res = []\\n    for f in films:\\n        if f['annee'] > annee:\\n            res.append(f['titre'])\\n    return res\\n\"\nelif kind == \"moyenne\":\n    fname, params = choice([\"moyenne_notes\", \"note_moyenne\"]), \"films\"\n    consigne = \"renvoie la **moyenne** des notes des films (la liste n'est pas vide)\"\n    for n in [4, 1, 5, 3, 2]:\n        L = films(n)\n        cases.append(((L,), sum(f[\"note\"] for f in L) / n))\n    ref = f\"def {fname}(films):\\n    total = 0\\n    for f in films:\\n        total = total + f['note']\\n    return total / len(films)\\n\"\nelse:\n    fname, params = choice([\"meilleur_film\", \"titre_du_meilleur\"]), \"films\"\n    consigne = \"renvoie le **titre** du film qui a la meilleure note (la liste n'est pas vide, les notes sont toutes différentes)\"\n    for n in [4, 1, 5, 3, 6]:\n        L = films(n)\n        cases.append(((L,), max(L, key=lambda f: f[\"note\"])[\"titre\"]))\n    ref = (f\"def {fname}(films):\\n    meilleur = films[0]\\n    for f in films:\\n        if f['note'] > meilleur['note']:\\n\"\n           f\"            meilleur = f\\n    return meilleur['titre']\\n\")\nexemple, attendu = cases[0]",
        "statement": "Une liste de films est une liste de dictionnaires de la forme `{'titre': ..., 'annee': ..., 'note': ...}`.\n\nÉcrire une fonction `{{ fname }}({{ params }})` qui {{ consigne }}.\n\nExemple : avec\n\n{{ code_block(\"films = \" + repr(exemple[0])) }}\n\n`{{ fname }}({{ \", \".join([\"films\"] + [repr(x) for x in exemple[1:]]) }})` renvoie `{{ repr(attendu) }}`.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "max",
              "sorted",
              "sort",
              "sum"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}",
        "hints": [
          "Dans `for f in films:`, la variable `f` est un dictionnaire : ses informations s'obtiennent avec `f['titre']`, `f['annee']`, `f['note']`.",
          "{{ {'titres': 'Commencez avec une liste vide et ajoutez-y les titres qui conviennent avec `append`.', 'moyenne': 'Additionnez les notes dans une variable, puis divisez par le nombre de films.', 'meilleur': 'Gardez dans une variable le meilleur film vu jusqu’ici (un dictionnaire), en partant du premier.'}[kind] }}"
        ]
      }
    },
    {
      "uid": "DICO-17",
      "title": "Écrire une fonction : dictionnaire de listes",
      "chapter": "Python : dictionnaires",
      "difficulty": 3,
      "skills": [
        "Données imbriquées : dictionnaire de listes",
        "Dictionnaires : calcul cumulatif",
        "Écrire une fonction"
      ],
      "template": {
        "code": "kind = choice([\"moyennes\", \"meilleur\", \"nb_notes\"])\ndef carnet(n):\n    return {p: sample(range(4, 20), randint(1, 4)) for p in sample(PRENOMS, n)}\ncases = []\nif kind == \"moyennes\":\n    fname, params = choice([\"moyennes\", \"calcul_moyennes\"]), \"notes\"\n    consigne = \"renvoie un **nouveau dictionnaire** qui associe à chaque élève la moyenne de ses notes\"\n    for n in [3, 0, 1, 4, 2]:\n        d = carnet(n)\n        cases.append(((d,), {p: sum(v) / len(v) for p, v in d.items()}))\n    ref = f\"def {fname}(notes):\\n    res = {{}}\\n    for eleve, liste in notes.items():\\n        res[eleve] = sum(liste) / len(liste)\\n    return res\\n\"\nelif kind == \"meilleur\":\n    fname, params = choice([\"meilleur_eleve\", \"premier\"]), \"notes\"\n    consigne = \"renvoie le nom de l'élève qui a la **meilleure moyenne** (le dictionnaire n'est pas vide et les moyennes sont toutes différentes)\"\n    for n in [3, 1, 4, 2, 5]:\n        while True:\n            d = carnet(n)\n            moy = [sum(v) / len(v) for v in d.values()]\n            if len(set(moy)) == len(moy):\n                break\n        cases.append(((d,), max(d, key=lambda p: sum(d[p]) / len(d[p]))))\n    ref = (f\"def {fname}(notes):\\n    meilleur = None\\n    for eleve, liste in notes.items():\\n        m = sum(liste) / len(liste)\\n\"\n           f\"        if meilleur is None or m > meilleure_moy:\\n            meilleur, meilleure_moy = eleve, m\\n    return meilleur\\n\")\nelse:\n    fname, params = choice([\"nb_notes\", \"total_notes\"]), \"notes\"\n    consigne = \"renvoie le **nombre total de notes** enregistrées, tous élèves confondus\"\n    for n in [3, 0, 1, 4, 5]:\n        d = carnet(n)\n        cases.append(((d,), sum(len(v) for v in d.values())))\n    ref = f\"def {fname}(notes):\\n    n = 0\\n    for liste in notes.values():\\n        n = n + len(liste)\\n    return n\\n\"\nexemple, attendu = cases[0]",
        "statement": "Les notes d'une classe sont rangées dans un dictionnaire qui associe à chaque élève la **liste** de ses notes (non vide), par exemple `{{ repr(exemple[0]) }}`.\n\nÉcrire une fonction `{{ fname }}({{ params }})` qui {{ consigne }}.\n\nExemple : `{{ fname }}({{ repr(exemple[0]) }})` renvoie `{{ repr(attendu) }}`.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}"
          }
        ],
        "solution": "{{ code_block(ref) }}",
        "hints": [
          "Parcourez `notes.items()` : à chaque tour vous obtenez un élève **et** sa liste de notes.",
          "Sur la liste d'un élève, `sum(liste)` et `len(liste)` donnent le total et le nombre de notes."
        ]
      }
    },
    {
      "uid": "DICO-18",
      "title": "Écrire une fonction : dictionnaire de dictionnaires",
      "chapter": "Python : dictionnaires",
      "difficulty": 3,
      "skills": [
        "Données imbriquées : dictionnaire de dictionnaires",
        "Écrire une fonction"
      ],
      "template": {
        "code": "kind = choice([\"habitants\", \"age_moyen\", \"plus_age\"])\ndef fiches(n):\n    return {p: {\"age\": a, \"ville\": choice(VILLES[:4])} for p, a in zip(sample(PRENOMS, n), sample(range(14, 20), n))}\ncases = []\nif kind == \"habitants\":\n    fname, params = choice([\"habitants\", \"qui_habite\"]), \"eleves, ville\"\n    consigne = \"renvoie la **liste des prénoms** des élèves qui habitent `ville`, dans l'ordre du dictionnaire\"\n    for n in [4, 0, 5, 3, 6]:\n        d = fiches(n)\n        v = choice(VILLES[:4])\n        cases.append(((d, v), [p for p, f in d.items() if f[\"ville\"] == v]))\n    ref = f\"def {fname}(eleves, ville):\\n    res = []\\n    for prenom, fiche in eleves.items():\\n        if fiche['ville'] == ville:\\n            res.append(prenom)\\n    return res\\n\"\nelif kind == \"age_moyen\":\n    fname, params = choice([\"age_moyen\", \"moyenne_age\"]), \"eleves\"\n    consigne = \"renvoie l'**âge moyen** des élèves (le dictionnaire n'est pas vide)\"\n    for n in [4, 1, 5, 3, 2]:\n        d = fiches(n)\n        cases.append(((d,), sum(f[\"age\"] for f in d.values()) / n))\n    ref = f\"def {fname}(eleves):\\n    total = 0\\n    for fiche in eleves.values():\\n        total = total + fiche['age']\\n    return total / len(eleves)\\n\"\nelse:\n    fname, params = choice([\"plus_age\", \"le_plus_vieux\"]), \"eleves\"\n    consigne = \"renvoie le **prénom** de l'élève le plus âgé (le dictionnaire n'est pas vide, les âges sont tous différents)\"\n    for n in [4, 1, 5, 3, 6]:\n        d = fiches(n)\n        cases.append(((d,), max(d, key=lambda p: d[p][\"age\"])))\n    ref = (f\"def {fname}(eleves):\\n    res = None\\n    for prenom in eleves:\\n\"\n           f\"        if res is None or eleves[prenom]['age'] > eleves[res]['age']:\\n            res = prenom\\n    return res\\n\")\nexemple, attendu = cases[0]",
        "statement": "Les fiches des élèves sont rangées dans un dictionnaire qui associe à chaque prénom un dictionnaire `{'age': ..., 'ville': ...}`.\n\nÉcrire une fonction `{{ fname }}({{ params }})` qui {{ consigne }}.\n\nExemple : avec\n\n{{ code_block(\"eleves = \" + repr(exemple[0])) }}\n\n`{{ fname }}({{ \", \".join([\"eleves\"] + [repr(x) for x in exemple[1:]]) }})` renvoie `{{ repr(attendu) }}`.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import copy\nfn = student.get(fname)\ncheck(callable(fn), f\"la fonction {fname} doit être définie\")\nif callable(fn):\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "max",
              "sorted",
              "sort",
              "sum"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}",
        "hints": [
          "Chaque valeur du dictionnaire est une fiche (un dictionnaire) : `eleves[prenom]['age']`, ou bien `fiche['age']` si vous parcourez `eleves.items()`.",
          "{{ {'habitants': 'Partez d’une liste vide et ajoutez le prénom quand la ville correspond.', 'age_moyen': 'Additionnez les âges puis divisez par le nombre d’élèves, `len(eleves)`.', 'plus_age': 'Gardez le prénom du plus âgé vu jusqu’ici, en partant de `None`.'}[kind] }}"
        ]
      }
    },
    {
      "uid": "DICO-19",
      "title": "Dictionnaire de dictionnaires : écrire l'instruction d'affichage",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : dictionnaire de dictionnaires",
        "Dictionnaires : accès et modification"
      ],
      "template": {
        "code": "def joli(d, nom):\n    lignes = [f\"    {k!r}: {v!r},\" for k, v in d.items()]\n    return nom + \" = {\\n\" + \"\\n\".join(lignes) + \"\\n}\"\n\ndef cible(consigne, expr):\n    ref = \"print(\" + expr + \")\"\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: data}), \"attendu2\": run(ref, namespace={nom: data2})}\n    require(c[\"attendu\"] != c[\"attendu2\"])\n    return c\n\nnom = choice([\"membres\", \"eleves\", \"fiches\", \"club\"])\npersonnes = sample(PRENOMS, 4)\nvilles = sample(VILLES, 4)\nages = sample(range(14, 19), 4)\ndata = {p: {\"age\": a, \"ville\": v} for p, a, v in zip(personnes, ages, villes)}\n# second jeu de données : mêmes prénoms, autres valeurs (sert à vérifier que l'élève lit bien le dictionnaire)\ndata2 = {p: {\"age\": a, \"ville\": v} for p, a, v in\n         zip(personnes, sample([a for a in range(11, 22) if a not in ages], 4), sample([v for v in VILLES if v not in villes], 4))}\np1, p2, p3 = sample(personnes, 3)\nmodeles = [\n    (lambda p: f\"la ville dans laquelle habite {p}\", lambda p: f\"{nom}[{p!r}]['ville']\"),\n    (lambda p: f\"l'âge de {p}\", lambda p: f\"{nom}[{p!r}]['age']\"),\n    (lambda p: f\"toute la fiche de {p} (le dictionnaire complet)\", lambda p: f\"{nom}[{p!r}]\"),\n    (lambda p: f\"l'âge qu'aura {p} l'an prochain\", lambda p: f\"{nom}[{p!r}]['age'] + 1\"),\n]\nm1, m2 = sample(modeles, 2)\nc1 = cible(m1[0](p1), m1[1](p1))\nc2 = cible(m2[0](p2), m2[1](p2))",
        "statement": "On dispose du dictionnaire suivant, **déjà défini** (inutile de le recopier) :\n\n{{ code_block(joli(data, nom)) }}\n\nPour chaque question, écrire l'instruction qui affiche la valeur demandée **en allant la chercher dans `{{ nom }}`** (et non en recopiant la valeur).",
        "fields": [
          {
            "type": "code",
            "label": "1. Instruction qui affiche {{ c1['consigne'] }}",
            "given": "{nom: data}",
            "tests": "c = c1\nsortie = student_output.strip()\nif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != c[\"attendu\"]:\n    check(False, f\"Votre code affiche `{sortie}`, alors qu'on attend `{c['attendu']}`.\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"], \"Le bon résultat s'affiche, mais votre instruction doit aller chercher la valeur \"\n          f\"dans le dictionnaire `{nom}` au lieu de l'écrire directement.\")",
            "reference": "{{ c1['ref'] }}"
          },
          {
            "type": "code",
            "label": "2. Instruction qui affiche {{ c2['consigne'] }}",
            "given": "{nom: data}",
            "tests": "c = c2\nsortie = student_output.strip()\nif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != c[\"attendu\"]:\n    check(False, f\"Votre code affiche `{sortie}`, alors qu'on attend `{c['attendu']}`.\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"], \"Le bon résultat s'affiche, mais votre instruction doit aller chercher la valeur \"\n          f\"dans le dictionnaire `{nom}` au lieu de l'écrire directement.\")",
            "reference": "{{ c2['ref'] }}"
          }
        ],
        "solution": "{{ code_block(c1['ref'] + \"\\n\" + c2['ref']) }}\n\n`{{ nom }}[prénom]` donne la fiche de la personne (un dictionnaire) ; un deuxième crochet va chercher une information dans cette fiche : `{{ nom }}[prénom]['ville']`.",
        "hints": [
          "`{{ nom }}[{{ repr(p3) }}]` donne toute la fiche de {{ p3 }} : c'est un dictionnaire. Un **deuxième crochet** permet d'y chercher une information.",
          "Par exemple, `print({{ nom }}[{{ repr(p3) }}]['age'])` afficherait l'âge de {{ p3 }}. Attention aux guillemets autour des chaînes (prénoms et noms de clés)."
        ]
      }
    },
    {
      "uid": "DICO-20",
      "title": "Dictionnaire de listes : écrire l'instruction d'affichage",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : dictionnaire de listes",
        "Listes : indices et tranches"
      ],
      "template": {
        "code": "def joli(d, nom):\n    lignes = [f\"    {k!r}: {v!r},\" for k, v in d.items()]\n    return nom + \" = {\\n\" + \"\\n\".join(lignes) + \"\\n}\"\n\ndef cible(consigne, expr):\n    ref = \"print(\" + expr + \")\"\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: data}), \"attendu2\": run(ref, namespace={nom: data2})}\n    require(c[\"attendu\"] != c[\"attendu2\"])\n    return c\n\nnom = choice([\"notes\", \"resultats\", \"releves\", \"carnet\"])\npersonnes = sample(PRENOMS, 4)\ndata = {p: sample(range(5, 20), randint(3, 5)) for p in personnes}\ndata2 = {p: sample(range(0, 21), randint(2, 6)) for p in personnes}\np1, p2, p3 = sample(personnes, 3)\nmodeles = [\n    (lambda p: f\"la liste des notes de {p}\", lambda p: f\"{nom}[{p!r}]\"),\n    (lambda p: f\"la première note de {p}\", lambda p: f\"{nom}[{p!r}][0]\"),\n    (lambda p: f\"la deuxième note de {p}\", lambda p: f\"{nom}[{p!r}][1]\"),\n    (lambda p: f\"la dernière note de {p}\", lambda p: f\"{nom}[{p!r}][-1]\"),\n    (lambda p: f\"le nombre de notes de {p}\", lambda p: f\"len({nom}[{p!r}])\"),\n    (lambda p: f\"la somme des notes de {p}\", lambda p: f\"sum({nom}[{p!r}])\"),\n]\nm1, m2 = sample(modeles, 2)\nc1 = cible(m1[0](p1), m1[1](p1))\nc2 = cible(m2[0](p2), m2[1](p2))",
        "statement": "On dispose du dictionnaire suivant, **déjà défini** (inutile de le recopier) :\n\n{{ code_block(joli(data, nom)) }}\n\nPour chaque question, écrire l'instruction qui affiche la valeur demandée **en allant la chercher dans `{{ nom }}`** (et non en recopiant la valeur).",
        "fields": [
          {
            "type": "code",
            "label": "1. Instruction qui affiche {{ c1['consigne'] }}",
            "given": "{nom: data}",
            "tests": "c = c1\nsortie = student_output.strip()\nif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != c[\"attendu\"]:\n    check(False, f\"Votre code affiche `{sortie}`, alors qu'on attend `{c['attendu']}`.\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"], \"Le bon résultat s'affiche, mais votre instruction doit aller chercher la valeur \"\n          f\"dans le dictionnaire `{nom}` au lieu de l'écrire directement.\")",
            "reference": "{{ c1['ref'] }}"
          },
          {
            "type": "code",
            "label": "2. Instruction qui affiche {{ c2['consigne'] }}",
            "given": "{nom: data}",
            "tests": "c = c2\nsortie = student_output.strip()\nif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != c[\"attendu\"]:\n    check(False, f\"Votre code affiche `{sortie}`, alors qu'on attend `{c['attendu']}`.\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"], \"Le bon résultat s'affiche, mais votre instruction doit aller chercher la valeur \"\n          f\"dans le dictionnaire `{nom}` au lieu de l'écrire directement.\")",
            "reference": "{{ c2['ref'] }}"
          }
        ],
        "solution": "{{ code_block(c1['ref'] + \"\\n\" + c2['ref']) }}\n\n`{{ nom }}[prénom]` est une **liste** : on peut lui appliquer un indice (`[0]` pour la première, `[-1]` pour la dernière), `len` ou `sum`.",
        "hints": [
          "`{{ nom }}[{{ repr(p3) }}]` est la liste des notes de {{ p3 }} : on peut lui appliquer tout ce qu'on fait sur une liste (indice entre crochets, `len`, `sum`).",
          "Par exemple, `print({{ nom }}[{{ repr(p3) }}][1])` afficherait la deuxième note de {{ p3 }} ; les indices commencent à 0 et `-1` désigne le dernier élément."
        ]
      }
    },
    {
      "uid": "LISTES-01",
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
      "uid": "LISTES-02",
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
      "uid": "LISTES-03",
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
      "uid": "LISTES-04",
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
      "uid": "REPR-01",
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
      "uid": "REPR-02",
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
      "uid": "REPR-03",
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
    }
  ]
}
```
