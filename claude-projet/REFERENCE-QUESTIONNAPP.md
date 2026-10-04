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
- **Boucles `while` imposées** (en 1ère NSI, toutes les boucles s'écrivent avec `while`) :
  mettre `"forbid": ["for"]` et, en tête des `tests`, vérifier avec `re` que `student_code`
  contient `while` et aucun `for` (ce qui exclut aussi les listes en compréhension) ; si ce
  n'est pas le cas, ne pas lancer les autres tests, pour que le score soit 0 (voir la banque
  `python-premiere-while.json`, variable `boucle_ok`). Écrire aussi la référence et le code
  montré à l'élève avec `while`.

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

Le fichier à produire a exactement cette structure (`format`, `version`, `title` et `description` de la banque, puis la liste `questions`). Chaque question : `title`, `chapter`, `difficulty` (1 facile, 2 moyen, 3 difficile), `skills` (liste), `template`. Voici les 72 questions de la banque fournie avec l'application, toutes testées : elles montrent les bons usages de chaque type de champ.

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
      "uid": "NSI1-01",
      "title": "Listes : append, concaténation et len",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Listes : indices et tranches",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "themes = [\n    (\"boissons\", [\"cafe\", \"the\", \"chocolat\", \"latte\", \"cappuccino\", \"moka\"]),\n    (\"saveurs\", [\"vanille\", \"caramel\", \"noisette\", \"cannelle\", \"coco\", \"menthe\"]),\n    (\"toppings\", [\"chantilly\", \"cacao\", \"sucre\", \"miel\", \"amandes\", \"biscuit\"]),\n]\n(n1, p1), (n2, p2) = sample(themes, 2)\nA = sample(p1, randint(2, 3))\nB = sample(p2, randint(2, 3))\najout = choice([x for x in p1 if x not in A])\ni = randint(1, len(A) + len(B))\nfin = choice([f\"print(len(menu), menu[{i}])\", f\"print(len({n1}), len(menu))\", f\"print(menu[{i}], menu[-1])\",\n              f\"print(menu[{len(A)}], len({n2}))\"])\nsrc = \"\\n\".join([f\"{n1} = {A!r}\", f\"{n2} = {B!r}\", f\"{n1}.append({ajout!r})\", f\"menu = {n1} + {n2}\", fin])\nout = run(src)\nmenu = evaluate(src, \"menu\")",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage",
            "answer": "out"
          }
        ],
        "solution": "Après `append`, `{{ n1 }}` contient {{ len(A) + 1 }} éléments ; `menu` vaut `{{ repr(menu) }}` ({{ len(menu) }} éléments, indices 0 à {{ len(menu) - 1 }}).\n\nLe programme affiche `{{ out }}`.",
        "hints": [
          "`append` ajoute **un** élément à la fin de la liste (et modifie la liste) ; `+` fabrique une **nouvelle** liste qui met les deux bout à bout.",
          "Écrivez `menu` en entier, puis numérotez ses éléments à partir de **0** ; `menu[-1]` est le dernier."
        ]
      }
    },
    {
      "uid": "NSI1-02",
      "title": "Listes : lire et modifier par indice",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Listes : indices et tranches",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nL = randlist(randint(5, 6), 1, 20)\nn = len(L)\ni, j = sample(range(n), 2)\nk = randint(2, 5)\nlignes = [f\"{nom} = {L!r}\", f\"{nom}[{i}] = {nom}[{j}] + {k}\",\n          choice([f\"x = {nom}[len({nom}) - 1]\", f\"x = {nom}[-2]\", f\"x = {nom}[{i}] * 2\", f\"x = {nom}[len({nom}) - {randint(2, n)}]\"]),\n          f\"{nom}[0] = x\",\n          f\"print({nom})\"]\nsrc = \"\\n\".join(lignes)\nout = run(src)",
        "statement": "Qu'affiche ce programme ? Écrire la liste comme Python l'affiche.\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage",
            "answer": "out",
            "ignore_spaces": true
          }
        ],
        "solution": "Le programme affiche `{{ out }}`.\n\n`{{ nom }}[i] = ...` remplace l'élément d'indice `i` ; les indices vont de `0` à `len({{ nom }}) - 1` = {{ n - 1 }}.",
        "hints": [
          "Recopiez la liste et numérotez ses éléments à partir de 0, puis appliquez les lignes **une par une** (chaque ligne travaille sur la liste déjà modifiée).",
          "`len({{ nom }})` vaut {{ n }} : le dernier élément est donc `{{ nom }}[{{ n - 1 }}]`, qu'on peut aussi écrire `{{ nom }}[-1]`."
        ]
      }
    },
    {
      "uid": "NSI1-03",
      "title": "Listes : pop, remove et append",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Listes : indices et tranches",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice([\"bulles\", \"L\", \"joueurs\", \"file\"])\nL = sample(PRENOMS, 5) if nom in (\"joueurs\", \"file\") else randlist(5, 1, 30, distinct=True)\na = choice(L)\nlignes = [f\"{nom} = {L!r}\"]\nops = [f\"{nom}.remove({a!r})\", f\"x = {nom}.pop({randint(0, 3)})\", f\"{nom}.append(x)\" if coin() else f\"{nom}.pop()\"]\nlignes += ops\nlignes.append(f\"print({nom}, len({nom}))\")\nsrc = \"\\n\".join(lignes)\nout = run(src)",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Affichage",
            "answer": "[out, out.replace(\"'\", '\"')]",
            "ignore_spaces": true
          }
        ],
        "solution": "Le programme affiche `{{ out }}`.\n\n- `{{ nom }}.pop(i)` retire l'élément d'**indice** `i` et le renvoie ; `{{ nom }}.pop()` retire le dernier.\n- `{{ nom }}.remove(v)` retire la première **valeur** égale à `v`.",
        "hints": [
          "Attention à la différence : `pop` reçoit un **indice** (une position), `remove` reçoit une **valeur**.",
          "Après chaque retrait, les éléments suivants se décalent : renumérotez la liste avant la ligne suivante."
        ]
      }
    },
    {
      "uid": "NSI1-04",
      "title": "Liste de listes : écrire l'instruction d'affichage",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : liste de listes",
        "Listes : indices et tranches"
      ],
      "template": {
        "code": "def cible(consigne, ref):\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: copy.deepcopy(data)}),\n         \"attendu2\": run(ref, namespace={nom: copy.deepcopy(data2)})}\n    require(c[\"attendu\"].strip() != c[\"attendu2\"].strip())\n    return c\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nimport copy\nif coin():\n    nom = \"C\"\n    noms = sample([\"sumatra\", \"moka\", \"java\", \"colombie\", \"kenya\", \"bresil\", \"guatemala\", \"ethiopie\"], 4)\n    data = [[c, round(randint(20, 60) / 10, 1)] for c in noms]\n    data2 = [[c, round(randint(20, 60) / 10, 1)] for c in noms]\n    quoi = \"chaque café avec son prix au kilo\"\n    ip = 1\n    unite = \"le prix du café\"\nelse:\n    nom = \"Livres\"\n    livres = sample([(\"Germinal\", \"Zola\"), (\"Candide\", \"Voltaire\"), (\"Le Cid\", \"Corneille\"), (\"Les Misérables\", \"Hugo\"),\n          (\"Le Petit Prince\", \"Saint-Exupéry\"), (\"Bel-Ami\", \"Maupassant\"), (\"Madame Bovary\", \"Flaubert\"),\n          (\"Phèdre\", \"Racine\")], 4)\n    data = [[t, a, randint(5, 25)] for t, a in livres]\n    data2 = [[t, a, randint(5, 25)] for t, a in livres]\n    noms = [t for t, a in livres]\n    quoi = \"chaque livre avec son titre, son auteur et son prix\"\n    ip = 2\n    unite = \"le prix du livre\"\ni1, i2 = sample(range(4), 2)\nmodeles = [\n    (lambda i: f\"{unite} « {noms[i]} »\", lambda i: f\"print({nom}[{i}][{ip}])\"),\n    (lambda i: f\"{unite} « {noms[i]} » augmenté de 1\", lambda i: f\"print({nom}[{i}][{ip}] + 1)\"),\n    (lambda i: f\"toute la liste qui décrit « {noms[i]} »\", lambda i: f\"print({nom}[{i}])\"),\n    (lambda i: f\"le double du prix de « {noms[i]} »\", lambda i: f\"print({nom}[{i}][{ip}] * 2)\"),\n]\nm1, m2 = sample(modeles, 2)\nc1 = cible(m1[0](i1), m1[1](i1))\nc2 = cible(m2[0](i2), m2[1](i2))",
        "statement": "La liste `{{ nom }}` décrit {{ quoi }}. Elle est **déjà définie** (inutile de la recopier) :\n\n{{ code_block(joli_liste(data, nom)) }}\n\nPour chaque question, écrire l'instruction qui affiche la valeur demandée **en allant la chercher dans `{{ nom }}`** (et non en recopiant la valeur).",
        "fields": [
          {
            "type": "code",
            "label": "1. Instruction qui affiche {{ c1['consigne'] }}",
            "given": "{nom: data}",
            "tests": "import re\nc = c1\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif False and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c1['ref'] }}"
          },
          {
            "type": "code",
            "label": "2. Instruction qui affiche {{ c2['consigne'] }}",
            "given": "{nom: data}",
            "tests": "import re\nc = c2\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif False and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c2['ref'] }}"
          }
        ],
        "solution": "{{ code_block(c1['ref'] + chr(10) + c2['ref']) }}\n\n`{{ nom }}[i]` est la **sous-liste** d'indice `i` ; un deuxième crochet va chercher un élément dans cette sous-liste : `{{ nom }}[i][{{ ip }}]` est son prix.",
        "hints": [
          "`{{ nom }}[0]` est la première sous-liste : `{{ repr(data[0]) }}`. Un **deuxième crochet** prend un élément dans cette sous-liste.",
          "Par exemple `{{ nom }}[0][{{ ip }}]` vaut `{{ repr(data[0][ip]) }}`. Repérez d'abord l'indice de la sous-liste qui vous intéresse (on compte à partir de 0)."
        ]
      }
    },
    {
      "uid": "NSI1-05",
      "title": "Liste de dictionnaires : écrire l'instruction d'affichage",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Données imbriquées : liste de dictionnaires",
        "Dictionnaires : accès et modification"
      ],
      "template": {
        "code": "def cible(consigne, ref):\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: copy.deepcopy(data)}),\n         \"attendu2\": run(ref, namespace={nom: copy.deepcopy(data2)})}\n    require(c[\"attendu\"].strip() != c[\"attendu2\"].strip())\n    return c\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nimport copy\nnom = \"films\"\ntitres = sample([\"Le Roi lion\", \"Titanic\", \"Coco\", \"Vaiana\", \"Ratatouille\", \"Inception\", \"Matrix\", \"Shrek\", \"Wall-E\", \"Avatar\"], 4)\ndef tirage():\n    return [{\"titre\": t, \"annee\": randint(1990, 2023), \"duree\": randint(80, 170)} for t in titres]\ndata, data2 = tirage(), tirage()\ni1, i2, i3 = sample(range(4), 3)\nmodeles = [\n    (lambda i: f\"l'année de sortie du film « {titres[i]} »\", lambda i: f\"print({nom}[{i}]['annee'])\"),\n    (lambda i: f\"la durée (en minutes) du film « {titres[i]} »\", lambda i: f\"print({nom}[{i}]['duree'])\"),\n    (lambda i: f\"tout le dictionnaire qui décrit le film « {titres[i]} »\", lambda i: f\"print({nom}[{i}])\"),\n    (lambda i: f\"la durée du film « {titres[i]} » diminuée de 10 minutes\", lambda i: f\"print({nom}[{i}]['duree'] - 10)\"),\n]\nm1, m2 = sample(modeles, 2)\nc1 = cible(m1[0](i1), m1[1](i1))\nc2 = cible(m2[0](i2), m2[1](i2))",
        "statement": "La liste `{{ nom }}` contient un dictionnaire par film. Elle est **déjà définie** (inutile de la recopier) :\n\n{{ code_block(joli_liste(data, nom)) }}\n\nPour chaque question, écrire l'instruction qui affiche la valeur demandée **en allant la chercher dans `{{ nom }}`**.",
        "fields": [
          {
            "type": "code",
            "label": "1. Instruction qui affiche {{ c1['consigne'] }}",
            "given": "{nom: data}",
            "tests": "import re\nc = c1\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif False and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c1['ref'] }}"
          },
          {
            "type": "code",
            "label": "2. Instruction qui affiche {{ c2['consigne'] }}",
            "given": "{nom: data}",
            "tests": "import re\nc = c2\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif False and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c2['ref'] }}"
          }
        ],
        "solution": "{{ code_block(c1['ref'] + chr(10) + c2['ref']) }}\n\n`{{ nom }}[i]` est un **dictionnaire** (on choisit le film par son indice dans la liste) ; on y lit une valeur par sa **clé** : `{{ nom }}[i]['annee']`.",
        "hints": [
          "`{{ nom }}[{{ i3 }}]` est le dictionnaire du film « {{ titres[i3] }} » : on choisit d'abord le film par son **indice** dans la liste (à partir de 0).",
          "Ensuite, on lit une valeur du dictionnaire par sa **clé** entre guillemets : `{{ nom }}[{{ i3 }}]['duree']` vaut {{ data[i3]['duree'] }}."
        ]
      }
    },
    {
      "uid": "NSI1-06",
      "title": "Dictionnaire : écrire les modifications",
      "chapter": "Python : dictionnaires",
      "difficulty": 1,
      "skills": [
        "Dictionnaires : accès et modification"
      ],
      "template": {
        "code": "if coin():\n    nom = choice([\"stocks\", \"Stocks\"])\n    cles = sample(FRUITS, 5)\n    data = {c: randint(3, 40) for c in cles[:4]}\n    unite = \"le stock de\"\nelse:\n    nom = \"scores\"\n    cles = sample(PRENOMS, 5)\n    data = {c: randint(3, 40) for c in cles[:4]}\n    unite = \"le score de\"\na, b = sample(cles[:4], 2)\nnouveau = cles[4]\nk = randint(2, 9)\nm = randint(1, 3)\nv = randint(5, 30)\nattendu = dict(data)\nattendu[a] = attendu[a] + k\nattendu[b] = attendu[b] - m\nattendu[nouveau] = v\nref = f\"{nom}[{a!r}] = {nom}[{a!r}] + {k}\\n{nom}[{b!r}] = {nom}[{b!r}] - {m}\\n{nom}[{nouveau!r}] = {v}\"",
        "statement": "Le dictionnaire `{{ nom }}` est **déjà défini** (inutile de le recopier) :\n\n{{ code_block(nom + \" = \" + repr(data)) }}\n\nÉcrire les instructions qui :\n\n1. augmentent {{ unite }} `{{ a }}` de {{ k }} ;\n2. diminuent {{ unite }} `{{ b }}` de {{ m }} ;\n3. ajoutent la clé `{{ nouveau }}` avec la valeur {{ v }}.",
        "fields": [
          {
            "type": "code",
            "label": "Vos instructions",
            "given": "{nom: data}",
            "reference": "{{ ref }}",
            "tests": "import re\nobtenu = student.get(nom)\nif re.search(r\"\\b\" + nom + r\"\\s*=\\s*[{d]\", student_code):\n    check(False, f\"Ne redéfinissez pas `{nom}` en entier : modifiez seulement les valeurs avec `{nom}[clé] = ...`.\")\nelif not isinstance(obtenu, dict):\n    check(False, f\"`{nom}` doit rester un dictionnaire.\")\nelse:\n    for cle in attendu:\n        if cle not in obtenu:\n            check(False, f\"la clé {cle!r} manque dans `{nom}`.\")\n        else:\n            check_equal(obtenu[cle], attendu[cle], f\"`{nom}[{cle!r}]` vaut {obtenu[cle]!r} au lieu de {attendu[cle]!r}.\")\n    for cle in obtenu:\n        if cle not in attendu:\n            check(False, f\"la clé {cle!r} ne devrait pas exister.\")"
          }
        ],
        "solution": "{{ code_block(ref) }}\n\n`{{ nom }}[clé] = valeur` modifie la valeur si la clé existe, et **crée** la clé sinon. On peut aussi écrire `{{ nom }}[{{ repr(a) }}] += {{ k }}`.",
        "hints": [
          "On lit une valeur avec `{{ nom }}[clé]` et on la remplace avec `{{ nom }}[clé] = nouvelle_valeur` ; la clé est une chaîne, donc entre guillemets.",
          "Pour augmenter : `{{ nom }}[{{ repr(a) }}] = {{ nom }}[{{ repr(a) }}] + {{ k }}`. Pour ajouter une clé, il suffit de lui affecter une valeur."
        ]
      }
    },
    {
      "uid": "NSI1-07",
      "title": "Qu'affiche cette boucle while ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Boucle while",
        "Parcours de liste",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nL = randlist(randint(5, 7), 1, 30, distinct=True)\nn = len(L)\nforme = choice([\"pas\", \"debut\", \"fin\", \"indice\", \"envers\"])\nif forme == \"pas\":\n    p = choice([2, 3])\n    corps = [\"i = 0\", f\"while i < len({nom}):\", f\"    print({nom}[i])\", f\"    i = i + {p}\"]\nelif forme == \"debut\":\n    s = randint(1, 2)\n    corps = [f\"i = {s}\", f\"while i < len({nom}):\", f\"    print({nom}[i])\", \"    i = i + 1\"]\nelif forme == \"fin\":\n    corps = [\"i = 0\", f\"while i < len({nom}) - {randint(1, 2)}:\", f\"    print({nom}[i])\", \"    i = i + 1\"]\nelif forme == \"indice\":\n    corps = [\"i = 0\", f\"while {nom}[i] != {L[randint(2, n - 1)]}:\", \"    print(i)\", \"    i = i + 1\"]\nelse:\n    corps = [f\"i = len({nom}) - 1\", \"while i >= 0:\", f\"    print({nom}[i])\", f\"    i = i - {choice([1, 2])}\"]\nsrc = f\"{nom} = {L!r}\\n\" + \"\\n\".join(corps)\nout = run(src)\nvals = out.split()",
        "statement": "Qu'affiche ce programme ? Écrire les valeurs affichées **dans l'ordre, séparées par des espaces**.\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "text",
            "label": "Valeurs affichées",
            "answer": "[' '.join(vals), ', '.join(vals), ','.join(vals), ' ; '.join(vals), chr(10).join(vals)]"
          }
        ],
        "solution": "Le programme affiche, une par ligne : `{{ ' '.join(vals) }}`.\n\nÀ chaque tour, la condition du `while` est testée **avant** d'exécuter le corps ; quand elle devient fausse, la boucle s'arrête.",
        "hints": [
          "Faites un tableau avec une colonne `i` : notez sa valeur à chaque tour, vérifiez la condition, puis notez ce qui est affiché.",
          "`len({{ nom }})` vaut {{ n }} ; les indices vont de 0 à {{ n - 1 }}. Regardez bien de combien `i` change à chaque tour, et par quelle valeur il commence."
        ]
      }
    },
    {
      "uid": "NSI1-08",
      "title": "Afficher les éléments d'une liste avec while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Parcours de liste"
      ],
      "template": {
        "code": "def cible(consigne, ref):\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: copy.deepcopy(data)}),\n         \"attendu2\": run(ref, namespace={nom: copy.deepcopy(data2)})}\n    require(c[\"attendu\"].strip() != c[\"attendu2\"].strip())\n    return c\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nimport copy\nnom = choice([\"fruits\", \"boissons\", \"prenoms\"])\npool = PRENOMS if nom == \"prenoms\" else (FRUITS if nom == \"fruits\" else [\"cafe\", \"the\", \"chocolat\", \"latte\", \"cappuccino\", \"moka\", \"jus\", \"limonade\"])\ndata = sample(pool, randint(4, 5))\ndata2 = sample(pool, randint(3, 6))\nconsignes = [\n    (\"chaque élément de la liste, un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i])\\n    i = i + 1\"),\n    (\"chaque élément précédé de son indice, un par ligne (par exemple `0 \" + data[0] + \"`)\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print(i, {nom}[i])\\n    i = i + 1\"),\n    (\"les éléments d'indice pair (indices 0, 2, 4…), un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i])\\n    i = i + 2\"),\n    (\"les éléments en commençant par le dernier, un par ligne\",\n     f\"i = len({nom}) - 1\\nwhile i >= 0:\\n    print({nom}[i])\\n    i = i - 1\"),\n]\nconsigne, ref = choice(consignes)\nc1 = cible(consigne, ref)",
        "statement": "La liste `{{ nom }}` est **déjà définie** (inutile de la recopier) :\n\n{{ code_block(nom + \" = \" + repr(data)) }}\n\nÉcrire un programme qui affiche **{{ c1['consigne'] }}**, à l'aide d'une boucle `while`. Votre programme doit fonctionner quelle que soit la liste (même avec un autre nombre d'éléments).",
        "fields": [
          {
            "type": "code",
            "label": "Votre programme",
            "given": "{nom: data}",
            "tests": "import re\nc = c1\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif True and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c1['ref'] }}",
            "forbid": [
              "for"
            ],
            "starter": "i = 0\nwhile "
          }
        ],
        "solution": "{{ code_block(c1['ref']) }}\n\nLe schéma d'un parcours avec `while` : on part d'un indice, on teste qu'il reste dans la liste, on traite `{{ nom }}[i]`, et on fait **avancer** `i` (sinon la boucle ne s'arrête jamais).",
        "hints": [
          "Un parcours avec `while` a trois parties : `i = ...` (indice de départ), `while condition:` (rester dans la liste), et dans la boucle `i = i + ...` pour avancer.",
          "Utilisez `len({{ nom }})` plutôt que le nombre {{ len(data) }} : votre programme sera testé avec une autre liste. Le dernier indice est `len({{ nom }}) - 1`."
        ]
      }
    },
    {
      "uid": "NSI1-09",
      "title": "Liste de dictionnaires : afficher les valeurs d'une clé",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Données imbriquées : liste de dictionnaires",
        "Parcours de liste"
      ],
      "template": {
        "code": "def cible(consigne, ref):\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: copy.deepcopy(data)}),\n         \"attendu2\": run(ref, namespace={nom: copy.deepcopy(data2)})}\n    require(c[\"attendu\"].strip() != c[\"attendu2\"].strip())\n    return c\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nimport copy\nnom = \"films\"\ndef tirage():\n    return [{\"titre\": t, \"annee\": randint(1990, 2023), \"duree\": randint(80, 170)}\n            for t in sample([\"Le Roi lion\", \"Titanic\", \"Coco\", \"Vaiana\", \"Ratatouille\", \"Inception\", \"Matrix\", \"Shrek\", \"Wall-E\", \"Avatar\"], randint(4, 5))]\ndata, data2 = tirage(), tirage()\nan = randint(2000, 2012)\nconsignes = [\n    (\"le titre de chaque film, un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i]['titre'])\\n    i = i + 1\"),\n    (\"l'année de sortie de chaque film, une par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i]['annee'])\\n    i = i + 1\"),\n    (\"le titre et la durée de chaque film, séparés par un espace, un film par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i]['titre'], {nom}[i]['duree'])\\n    i = i + 1\"),\n    (f\"le titre des films sortis **après {an}** (strictement), un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    if {nom}[i]['annee'] > {an}:\\n        print({nom}[i]['titre'])\\n    i = i + 1\"),\n]\nconsigne, ref = choice(consignes)\nc1 = cible(consigne, ref)",
        "statement": "La liste `{{ nom }}` est **déjà définie** (inutile de la recopier) :\n\n{{ code_block(joli_liste(data, nom)) }}\n\nÉcrire un programme qui affiche {{ c1['consigne'] }}, à l'aide d'une boucle `while`. Il doit fonctionner avec n'importe quelle liste de films.",
        "fields": [
          {
            "type": "code",
            "label": "Votre programme",
            "given": "{nom: data}",
            "tests": "import re\nc = c1\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif True and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c1['ref'] }}",
            "forbid": [
              "for"
            ],
            "starter": "i = 0\nwhile "
          }
        ],
        "solution": "{{ code_block(c1['ref']) }}\n\n`{{ nom }}[i]` est le dictionnaire du film d'indice `i` ; `{{ nom }}[i]['titre']` est son titre.",
        "hints": [
          "Parcourez la liste avec un indice `i` comme d'habitude ; à chaque tour, `{{ nom }}[i]` est **un dictionnaire** (un film).",
          "Dans ce dictionnaire, on lit une valeur par sa clé : `{{ nom }}[i]['titre']`, `{{ nom }}[i]['annee']`, `{{ nom }}[i]['duree']`."
        ]
      }
    },
    {
      "uid": "NSI1-10",
      "title": "Liste de listes : afficher avec while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Données imbriquées : liste de listes",
        "Parcours de liste"
      ],
      "template": {
        "code": "def cible(consigne, ref):\n    c = {\"consigne\": consigne, \"ref\": ref,\n         \"attendu\": run(ref, namespace={nom: copy.deepcopy(data)}),\n         \"attendu2\": run(ref, namespace={nom: copy.deepcopy(data2)})}\n    require(c[\"attendu\"].strip() != c[\"attendu2\"].strip())\n    return c\n\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\n\nimport copy\nif coin():\n    nom = \"C\"\n    def tirage():\n        return [[c, round(randint(20, 60) / 10, 1)] for c in sample([\"sumatra\", \"moka\", \"java\", \"colombie\", \"kenya\", \"bresil\", \"guatemala\", \"ethiopie\"], randint(3, 5))]\n    ip, objet, seuil = 1, \"café\", choice([3.5, 4, 4.5])\nelse:\n    nom = \"Livres\"\n    def tirage():\n        return [[t, a, randint(5, 25)] for t, a in sample([(\"Germinal\", \"Zola\"), (\"Candide\", \"Voltaire\"), (\"Le Cid\", \"Corneille\"), (\"Les Misérables\", \"Hugo\"),\n          (\"Le Petit Prince\", \"Saint-Exupéry\"), (\"Bel-Ami\", \"Maupassant\"), (\"Madame Bovary\", \"Flaubert\"),\n          (\"Phèdre\", \"Racine\")], randint(3, 5))]\n    ip, objet, seuil = 2, \"livre\", choice([10, 12, 15])\ndata, data2 = tirage(), tirage()\nconsignes = [\n    (f\"le prix de chaque {objet}, un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i][{ip}])\\n    i = i + 1\"),\n    (f\"le nom de chaque {objet} suivi de son prix, un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i][0], {nom}[i][{ip}])\\n    i = i + 1\"),\n    (f\"le nom des {objet}s dont le prix est **inférieur ou égal à {seuil}**, un par ligne\",\n     f\"i = 0\\nwhile i < len({nom}):\\n    if {nom}[i][{ip}] <= {seuil}:\\n        print({nom}[i][0])\\n    i = i + 1\"),\n]\nconsigne, ref = choice(consignes)\nc1 = cible(consigne, ref)",
        "statement": "La liste `{{ nom }}` est **déjà définie** (inutile de la recopier) ; chaque sous-liste décrit un {{ objet }} :\n\n{{ code_block(joli_liste(data, nom)) }}\n\nÉcrire un programme qui affiche {{ c1['consigne'] }}, à l'aide d'une boucle `while`. Il doit fonctionner avec n'importe quelle liste de ce type.",
        "fields": [
          {
            "type": "code",
            "label": "Votre programme",
            "given": "{nom: data}",
            "tests": "import re\nc = c1\n_code = re.sub(r\"#.*\", \"\", student_code)\nsortie = student_output.strip()\nattendu = c[\"attendu\"].strip()\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`).\")\nelif True and not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelif not sortie:\n    check(False, \"Votre code n'affiche rien : utilisez `print(...)`.\")\nelif sortie != attendu:\n    check(False, \"Votre code affiche `\" + \" / \".join(sortie.splitlines()) + \"` alors qu'on attend `\"\n          + \" / \".join(attendu.splitlines()) + \"` (le / sépare les lignes).\")\nelse:\n    try:\n        autre = rerun({nom: data2}).strip()\n    except Exception:\n        autre = None\n    check(autre == c[\"attendu2\"].strip(), \"Le bon résultat s'affiche, mais votre code doit aller chercher les valeurs \"\n          f\"dans `{nom}` au lieu de les écrire directement.\")",
            "reference": "{{ c1['ref'] }}",
            "forbid": [
              "for"
            ],
            "starter": "i = 0\nwhile "
          }
        ],
        "solution": "{{ code_block(c1['ref']) }}\n\n`{{ nom }}[i]` est la sous-liste d'indice `i` ; `{{ nom }}[i][0]` est le nom et `{{ nom }}[i][{{ ip }}]` le prix.",
        "hints": [
          "Parcourez `{{ nom }}` avec un indice `i` ; à chaque tour, `{{ nom }}[i]` est une **sous-liste**, par exemple `{{ repr(data[0]) }}`.",
          "Le prix est à l'indice {{ ip }} de la sous-liste : `{{ nom }}[i][{{ ip }}]`. N'oubliez pas `i = i + 1` à la fin du corps de la boucle."
        ]
      }
    },
    {
      "uid": "NSI1-11",
      "title": "Quelle boucle while parcourt toute la liste ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Boucle while",
        "Parcours de liste"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nL = randlist(4, 1, 9, distinct=True)\nbonne = (f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i])\\n    i = i + 1\",\n         \"affiche bien chaque élément, du premier au dernier.\")\nmauvaises = [\n    (f\"i = 0\\nwhile i <= len({nom}):\\n    print({nom}[i])\\n    i = i + 1\",\n     f\"provoque une erreur `IndexError` : au dernier tour `i` vaut {len(L)}, or le dernier indice est {len(L) - 1}.\"),\n    (f\"i = 1\\nwhile i < len({nom}):\\n    print({nom}[i])\\n    i = i + 1\",\n     \"oublie le premier élément : les indices commencent à 0.\"),\n    (f\"i = 0\\nwhile i < len({nom}) - 1:\\n    print({nom}[i])\\n    i = i + 1\",\n     \"oublie le dernier élément : la boucle s'arrête avant l'indice `len - 1`.\"),\n    (f\"i = 0\\nwhile i < len({nom}):\\n    print(i)\\n    i = i + 1\",\n     \"affiche les **indices** 0, 1, 2… et non les éléments.\"),\n    (f\"i = 0\\nwhile i < len({nom}):\\n    print({nom}[i])\\ni = i + 1\",\n     \"ne s'arrête jamais : `i = i + 1` n'est pas indenté, il est en dehors de la boucle, donc `i` reste à 0.\"),\n    (f\"i = 0\\nwhile i < len({nom}):\\n    i = i + 1\\n    print({nom}[i])\",\n     \"oublie le premier élément puis provoque une erreur `IndexError` : `i` augmente **avant** l'affichage.\"),\n]\nchoisis = shuffled([bonne] + sample(mauvaises, 3))\noptions = [(\"```python\\n\" + c + \"\\n```\", c == bonne[0]) for c, _ in choisis]\nexpl = \"\\n\\n\".join(\"```python\\n\" + c + \"\\n```\\n\" + (\"**Bonne réponse** : ce programme \" if c == bonne[0] else \"Ce programme \") + e\n                     for c, e in choisis)",
        "statement": "On dispose de la liste `{{ nom }} = {{ repr(L) }}`.\n\nQuel programme affiche **tous** les éléments de `{{ nom }}`, un par ligne ?",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "options",
            "shuffle": false
          }
        ],
        "solution": "{{ expl }}\n\nLe schéma correct : départ à `i = 0`, condition `i < len({{ nom }})`, et `i = i + 1` **dans** la boucle, après le traitement de `{{ nom }}[i]`.",
        "hints": [
          "Faites tourner chaque programme à la main sur la liste `{{ repr(L) }}` : quelle est la première valeur de `i`, et la dernière pour laquelle on exécute le corps ?",
          "Vérifiez trois choses : l'indice de départ (0), la condition (le dernier indice est `len({{ nom }}) - 1`), et l'indentation de `i = i + 1`."
        ],
        "max_tries": 2
      }
    },
    {
      "uid": "NSI1-12",
      "title": "Compter avec une boucle while : qu'affiche ce programme ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Boucle while",
        "Compter des occurrences",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nL = [randint(1, 6) for _ in range(randint(7, 9))]\nx = choice(L)\ncond, texte = choice([\n    (f\"{nom}[i] == {x}\", f\"égaux à {x}\"),\n    (f\"{nom}[i] > {x}\", f\"strictement supérieurs à {x}\"),\n    (f\"{nom}[i] % 2 == 0\", \"pairs\"),\n    (f\"{nom}[i] != {x}\", f\"différents de {x}\"),\n])\nsrc = \"\\n\".join([f\"{nom} = {L!r}\", \"n = 0\", \"i = 0\", f\"while i < len({nom}):\",\n                 f\"    if {cond}:\", \"        n = n + 1\", \"    i = i + 1\", \"print(n)\"])\nrep = int(run(src))",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Valeur affichée",
            "answer": "rep"
          }
        ],
        "solution": "Le programme compte les éléments {{ texte }} : il affiche **{{ rep }}**.\n\n`n` est un **compteur** : il part de 0 et augmente de 1 chaque fois que la condition est vraie.",
        "hints": [
          "`n` augmente de 1 seulement quand la condition du `if` est vraie. Passez les éléments un par un.",
          "Cette boucle compte les éléments de `{{ nom }}` {{ texte }}. Entourez-les dans la liste et comptez-les."
        ]
      }
    },
    {
      "uid": "NSI1-13",
      "title": "Écrire compte(x, L) avec while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Compter des occurrences",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname = choice([\"compte\", \"nb_occurrences\", \"occurrences\"])\nparams = \"x, L\"\ndef fabrique():\n    L = [randint(1, 5) for _ in range(randint(5, 9))]\n    return L\ncases = []\nfor _ in range(3):\n    L = fabrique()\n    x = choice(L)\n    cases.append(((x, L), L.count(x)))\ncases.append(((9, fabrique()), 0))\ncases.append(((3, []), 0))\nnoms = sample(FRUITS, 3)\nL = [choice(noms) for _ in range(6)]\ncases.append(((noms[0], L), L.count(noms[0])))\nref = f\"def {fname}(x, L):\\n    n = 0\\n    i = 0\\n    while i < len(L):\\n        if L[i] == x:\\n            n = n + 1\\n        i = i + 1\\n    return n\"\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}(x, L)` qui **renvoie** le nombre de fois où la valeur `x` apparaît dans la liste `L`.\n\nPar exemple, `{{ fname }}({{ repr(ex[0][0]) }}, {{ repr(ex[0][1]) }})` renvoie `{{ ex[1] }}`.\n\nContraintes : utiliser une boucle `while` ; `for` et la méthode `count` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "count"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn parcourt la liste avec un indice `i` et on augmente un compteur `n` chaque fois que `L[i]` est égal à `x`. Le `return` est **après** la boucle.",
        "hints": [
          "Il faut un **compteur** `n = 0` avant la boucle, et un indice `i` pour parcourir `L` ; dans la boucle, comparez `L[i]` à `x`.",
          "Le `return n` doit être **en dehors** de la boucle (moins indenté) : sinon la fonction s'arrête au premier tour. Pensez aussi à la liste vide."
        ]
      }
    },
    {
      "uid": "NSI1-14",
      "title": "Compter dans une liste de dictionnaires",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Compter des occurrences",
        "Données imbriquées : liste de dictionnaires",
        "Écrire une fonction"
      ],
      "template": {
        "code": "if coin():\n    fname, params, cle, objet = \"nb_films_longs\", \"films, duree_min\", \"duree\", \"films\"\n    def fab(n):\n        return [{\"titre\": t, \"duree\": randint(80, 170)} for t in sample([\"Le Roi lion\", \"Titanic\", \"Coco\", \"Vaiana\", \"Ratatouille\", \"Inception\", \"Matrix\", \"Shrek\", \"Wall-E\", \"Avatar\"], n)]\n    texte = \"le nombre de films dont la durée (clé `\\\"duree\\\"`) est **supérieure ou égale** à `duree_min`\"\n    seuils = [100, 120, 140]\nelse:\n    fname, params, cle, objet = \"nb_majeurs\", \"eleves, age_min\", \"age\", \"eleves\"\n    def fab(n):\n        return [{\"nom\": p, \"age\": randint(14, 20)} for p in sample(PRENOMS, n)]\n    texte = \"le nombre d'élèves dont l'âge (clé `\\\"age\\\"`) est **supérieur ou égal** à `age_min`\"\n    seuils = [16, 17, 18]\ncases = []\nfor n in (4, 5, 6):\n    L = fab(n)\n    s = choice(seuils)\n    cases.append(((L, s), len([e for e in L if e[cle] >= s])))\ncases.append((([], seuils[0]), 0))\np = params.split(\", \")\nref = (f\"def {fname}({params}):\\n    n = 0\\n    i = 0\\n    while i < len({p[0]}):\\n\"\n       f\"        if {p[0]}[i]['{cle}'] >= {p[1]}:\\n            n = n + 1\\n        i = i + 1\\n    return n\")\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui **renvoie** {{ texte }}.\n\nExemple :\n\n{{ code_block(params.split(', ')[0] + \" = \" + repr(ex[0][0]) + chr(10) + fname + \"(\" + params.split(', ')[0] + \", \" + str(ex[0][1]) + \")   # renvoie \" + str(ex[1])) }}\n\nContrainte : utiliser une boucle `while` (pas de `for`).",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nÀ chaque tour, `{{ params.split(', ')[0] }}[i]` est un dictionnaire ; on compare sa valeur `['{{ cle }}']` au seuil.",
        "hints": [
          "C'est un comptage : un compteur à 0 avant la boucle, `+ 1` quand la condition est vraie, et `return` après la boucle.",
          "La condition porte sur `{{ params.split(', ')[0] }}[i]['{{ cle }}']` (on choisit l'élément par son indice, puis la valeur par sa clé)."
        ]
      }
    },
    {
      "uid": "NSI1-15",
      "title": "Cumuler avec une boucle while : qu'affiche ce programme ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 1,
      "skills": [
        "Boucle while",
        "Calcul cumulatif",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "nom = choice(NOMS_LISTES)\nL = randlist(randint(5, 6), 1, 12)\nk = choice(L)\nforme = choice([\"somme\", \"pas\", \"si\", \"indices\"])\nif forme == \"somme\":\n    corps = [f\"    s = s + {nom}[i]\", \"    i = i + 1\"]\nelif forme == \"pas\":\n    corps = [f\"    s = s + {nom}[i]\", \"    i = i + 2\"]\nelif forme == \"si\":\n    corps = [f\"    if {nom}[i] > {k}:\", f\"        s = s + {nom}[i]\", \"    i = i + 1\"]\nelse:\n    corps = [\"    s = s + i\", \"    i = i + 1\"]\nsrc = \"\\n\".join([f\"{nom} = {L!r}\", \"s = 0\", \"i = 0\", f\"while i < len({nom}):\"] + corps + [\"print(s)\"])\nrep = int(run(src))",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Valeur affichée",
            "answer": "rep"
          }
        ],
        "solution": "Le programme affiche **{{ rep }}**.\n\n`s` est un **accumulateur** : il part de 0 et, à chaque tour concerné, on lui ajoute une valeur.",
        "hints": [
          "Faites un tableau avec les colonnes `i` et `s`, et remplissez une ligne par tour de boucle.",
          "Regardez précisément ce qu'on ajoute à `s` : l'élément `{{ nom }}[i]` ou l'indice `i` ? À chaque tour ou seulement sous condition ?"
        ]
      }
    },
    {
      "uid": "NSI1-16",
      "title": "Écrire une fonction de somme avec while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Calcul cumulatif",
        "Écrire une fonction"
      ],
      "template": {
        "code": "variante = choice([\"somme\", \"somme_pairs\", \"somme_positifs\"])\nfname, params = variante, \"L\"\ncond = {\"somme\": None, \"somme_pairs\": \"L[i] % 2 == 0\", \"somme_positifs\": \"L[i] > 0\"}[variante]\ntexte = {\"somme\": \"la somme des éléments de la liste `L`\",\n         \"somme_pairs\": \"la somme des éléments **pairs** de la liste `L`\",\n         \"somme_positifs\": \"la somme des éléments **strictement positifs** de la liste `L`\"}[variante]\ndef attendu(L):\n    s = 0\n    for x in L:\n        if cond is None or (x % 2 == 0 if variante == \"somme_pairs\" else x > 0):\n            s = s + x\n    return s\ncases = []\nfor n in (4, 6, 7):\n    L = randlist(n, -9 if variante == \"somme_positifs\" else 1, 30)\n    cases.append(((L,), attendu(L)))\ncases.append((([],), 0))\nif cond:\n    corps = f\"        if {cond}:\\n            s = s + L[i]\\n\"\nelse:\n    corps = \"        s = s + L[i]\\n\"\nref = f\"def {fname}(L):\\n    s = 0\\n    i = 0\\n    while i < len(L):\\n{corps}        i = i + 1\\n    return s\"\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}(L)` qui **renvoie** {{ texte }} (0 si la liste est vide).\n\nPar exemple, `{{ fname }}({{ repr(ex[0][0]) }})` renvoie `{{ ex[1] }}`.\n\nContraintes : utiliser une boucle `while` ; `for` et `sum` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "sum"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn utilise un **accumulateur** `s` qui part de 0 ; à chaque tour (concerné), on lui ajoute `L[i]`.",
        "hints": [
          "Il faut deux variables avant la boucle : l'accumulateur `s = 0` et l'indice `i = 0`.",
          "Dans la boucle : ajouter `L[i]` à `s`{{ ' seulement si la condition est vraie' if cond else '' }}, puis `i = i + 1`. Le `return s` vient **après** la boucle."
        ]
      }
    },
    {
      "uid": "NSI1-17",
      "title": "Total dans une liste de listes ou de dictionnaires",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Calcul cumulatif",
        "Données imbriquées : liste de listes",
        "Écrire une fonction"
      ],
      "template": {
        "code": "if coin():\n    fname, params = \"prix_total\", \"livres\"\n    def fab(n):\n        return [[t, a, randint(5, 25)] for t, a in sample([(\"Germinal\", \"Zola\"), (\"Candide\", \"Voltaire\"), (\"Le Cid\", \"Corneille\"), (\"Les Misérables\", \"Hugo\"),\n          (\"Le Petit Prince\", \"Saint-Exupéry\"), (\"Bel-Ami\", \"Maupassant\"), (\"Madame Bovary\", \"Flaubert\"),\n          (\"Phèdre\", \"Racine\")], n)]\n    acces, texte = \"livres[i][2]\", \"le prix total des livres ; chaque livre est une liste `[titre, auteur, prix]`\"\n    def tot(L):\n        return sum(x[2] for x in L)\nelse:\n    fname, params = \"duree_totale\", \"films\"\n    def fab(n):\n        return [{\"titre\": t, \"annee\": randint(1990, 2023), \"duree\": randint(80, 170)} for t in sample([\"Le Roi lion\", \"Titanic\", \"Coco\", \"Vaiana\", \"Ratatouille\", \"Inception\", \"Matrix\", \"Shrek\", \"Wall-E\", \"Avatar\"], n)]\n    acces, texte = \"films[i]['duree']\", \"la durée totale (en minutes) des films ; chaque film est un dictionnaire de clés `\\\"titre\\\"`, `\\\"annee\\\"` et `\\\"duree\\\"`\"\n    def tot(L):\n        return sum(x[\"duree\"] for x in L)\ncases = [((L,), tot(L)) for L in (fab(3), fab(4), fab(5))] + [(([],), 0)]\nref = f\"def {fname}({params}):\\n    s = 0\\n    i = 0\\n    while i < len({params}):\\n        s = s + {acces}\\n        i = i + 1\\n    return s\"\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui **renvoie** {{ texte }}.\n\nExemple :\n\n{{ code_block(params + \" = \" + repr(ex[0][0]) + chr(10) + fname + \"(\" + params + \")   # renvoie \" + str(ex[1])) }}\n\nContraintes : utiliser une boucle `while` ; `for` et `sum` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "sum"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nC'est une somme classique ; la seule différence est la façon d'atteindre la valeur : `{{ acces }}`.",
        "hints": [
          "Même schéma qu'une somme : `s = 0`, `i = 0`, une boucle `while` sur les indices, et `return s` après la boucle.",
          "À chaque tour, la valeur à ajouter est `{{ acces }}`."
        ]
      }
    },
    {
      "uid": "NSI1-18",
      "title": "Écrire max_liste(L) ou min_liste(L) avec while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Recherche de max/min",
        "Écrire une fonction"
      ],
      "template": {
        "code": "sens = choice([\"max\", \"min\"])\nfname, params = sens + \"_liste\", \"L\"\ncases = []\nfor n in (4, 5, 7):\n    L = randlist(n, -40, -1) if (n == 4 and sens == \"max\") else randlist(n, -20, 50)\n    if n == 4 and sens == \"min\":\n        L = randlist(n, 1, 40)\n    cases.append(((L,), max(L) if sens == \"max\" else min(L)))\nc = randint(-9, 9)\ncases.append((([c],), c))\nop = \">\" if sens == \"max\" else \"<\"\nref = f\"def {fname}(L):\\n    m = L[0]\\n    i = 1\\n    while i < len(L):\\n        if L[i] {op} m:\\n            m = L[i]\\n        i = i + 1\\n    return m\"\nex = cases[2]\nmot = \"le plus grand\" if sens == \"max\" else \"le plus petit\"",
        "statement": "Écrire une fonction `{{ fname }}(L)` qui **renvoie** {{ mot }} élément d'une liste `L` de nombres **non vide**.\n\nPar exemple, `{{ fname }}({{ repr(ex[0][0]) }})` renvoie `{{ ex[1] }}`.\n\nContraintes : utiliser une boucle `while` ; `for`, `max`, `min`, `sorted` et `sort` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "max",
              "min",
              "sorted",
              "sort"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn garde dans `m` {{ mot }} élément **vu jusqu'ici** ; on l'initialise avec `L[0]` (et non 0, qui ne marcherait pas si tous les nombres sont {{ 'négatifs' if sens == 'max' else 'positifs' }}).",
        "hints": [
          "Gardez dans une variable `m` {{ mot }} élément rencontré jusqu'ici, et comparez-le à chaque `L[i]`.",
          "Initialisez `m` avec le premier élément `L[0]`, pas avec 0 : la fonction est testée sur une liste où tous les nombres sont {{ 'négatifs' if sens == 'max' else 'positifs' }}."
        ]
      }
    },
    {
      "uid": "NSI1-19",
      "title": "Tous les éléments vérifient-ils la condition ? (while)",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Tester une condition sur tous les éléments",
        "Écrire une fonction"
      ],
      "template": {
        "code": "variante = choice([\"pairs\", \"positifs\", \"inferieurs\"])\nif variante == \"pairs\":\n    fname, params, cond, texte = \"tous_pairs\", \"L\", \"L[i] % 2 != 0\", \"`True` si **tous** les éléments de `L` sont pairs, `False` sinon\"\n    def bon():\n        return 2 * randint(-10, 30)\n    def mauvais():\n        return 2 * randint(-10, 30) + 1\nelif variante == \"positifs\":\n    fname, params, cond, texte = \"tous_positifs\", \"L\", \"L[i] <= 0\", \"`True` si **tous** les éléments de `L` sont strictement positifs, `False` sinon\"\n    def bon():\n        return randint(1, 50)\n    def mauvais():\n        return randint(-20, 0)\nelse:\n    fname, params, cond, texte = \"tous_inferieurs\", \"L, n\", \"L[i] >= n\", \"`True` si **tous** les éléments de `L` sont strictement inférieurs à `n`, `False` sinon\"\n    seuil = randint(20, 40)\n    def bon():\n        return randint(0, seuil - 1)\n    def mauvais():\n        return randint(seuil, seuil + 20)\nextra = (seuil,) if variante == \"inferieurs\" else ()\ndef liste(pos):\n    L = [bon() for _ in range(5)]\n    if pos is not None:\n        L[pos] = mauvais()\n    return L\ncases = [((liste(None),) + extra, True), ((liste(0),) + extra, False), ((liste(2),) + extra, False),\n         ((liste(4),) + extra, False), ((liste(None),) + extra, True), (([],) + extra, True)]\nref = f\"def {fname}({params}):\\n    i = 0\\n    while i < len(L):\\n        if {cond}:\\n            return False\\n        i = i + 1\\n    return True\"\nex = cases[3]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui **renvoie** {{ texte }}. Pour une liste vide, elle renvoie `True`.\n\nPar exemple, `{{ fname }}({{ \", \".join(repr(a) for a in ex[0]) }})` renvoie `{{ ex[1] }}`.\n\nContraintes : utiliser une boucle `while` ; `for`, `all` et `any` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "all",
              "any"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nDès qu'un élément ne respecte pas la condition, on peut répondre `False` tout de suite. On ne peut répondre `True` qu'**après** avoir vérifié tous les éléments, donc après la boucle.",
        "hints": [
          "Cherchez un **contre-exemple** : dès qu'un élément ne convient pas, la fonction peut renvoyer `False`.",
          "Le `return True` doit être **après** la boucle : tant qu'on n'a pas tout vérifié, on ne peut pas conclure que tous les éléments conviennent."
        ]
      }
    },
    {
      "uid": "NSI1-20",
      "title": "Une fonction « tous » qui se trompe ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 3,
      "skills": [
        "Boucle while",
        "Tester une condition sur tous les éléments",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "fname = choice([\"tous_pairs\", \"verif\", \"test_pairs\"])\nversion = choice([\"juste\", \"premier\", \"existe\"])\nif version == \"juste\":\n    corps = [\"    i = 0\", \"    while i < len(L):\", \"        if L[i] % 2 != 0:\", \"            return False\", \"        i = i + 1\", \"    return True\"]\nelif version == \"premier\":\n    corps = [\"    i = 0\", \"    while i < len(L):\", \"        if L[i] % 2 != 0:\", \"            return False\", \"        else:\",\n             \"            return True\", \"        i = i + 1\", \"    return True\"]\nelse:\n    corps = [\"    i = 0\", \"    while i < len(L):\", \"        if L[i] % 2 == 0:\", \"            return True\", \"        i = i + 1\", \"    return False\"]\nsrc = f\"def {fname}(L):\\n\" + \"\\n\".join(corps)\npair = lambda: 2 * randint(1, 20)\nimpair = lambda: 2 * randint(1, 20) + 1\nL1 = [pair() for _ in range(4)]\nL2 = [pair(), pair(), impair(), pair()]\nL3 = [impair(), pair(), impair(), impair()]\nlistes = shuffled([L1, L2, L3])\nreps = [repr(evaluate(src, f\"{fname}({L!r})\")) for L in listes]\navis = {\"juste\": \"Cette fonction est **correcte** : elle renvoie `False` dès qu'un élément est impair, et `True` seulement après avoir tout vérifié.\",\n        \"premier\": \"Cette fonction est **fausse** : au premier tour, elle renvoie forcément `True` ou `False`, donc elle ne regarde que le **premier** élément.\",\n        \"existe\": \"Cette fonction est **fausse** : elle renvoie `True` dès qu'elle trouve **un** élément pair ; elle teste donc s'il **existe** un élément pair, pas si **tous** le sont.\"}[version]",
        "statement": "On veut une fonction qui renvoie `True` si **tous** les éléments de la liste sont pairs. Voici une proposition :\n\n{{ code_block(src) }}\n\nQue renvoient les appels suivants ? (répondre `True` ou `False`)",
        "fields": [
          {
            "type": "text",
            "label": "`{{ fname }}({{ repr(listes[0]) }})`",
            "answer": "[reps[0], reps[0].lower()]"
          },
          {
            "type": "text",
            "label": "`{{ fname }}({{ repr(listes[1]) }})`",
            "answer": "[reps[1], reps[1].lower()]"
          },
          {
            "type": "text",
            "label": "`{{ fname }}({{ repr(listes[2]) }})`",
            "answer": "[reps[2], reps[2].lower()]"
          }
        ],
        "solution": "Les appels renvoient `{{ reps[0] }}`, `{{ reps[1] }}` et `{{ reps[2] }}`.\n\n{{ avis }}\n\nLa bonne version :\n\n{{ code_block(\"def tous_pairs(L):\" + chr(10) + \"    i = 0\" + chr(10) + \"    while i < len(L):\" + chr(10) + \"        if L[i] % 2 != 0:\" + chr(10) + \"            return False\" + chr(10) + \"        i = i + 1\" + chr(10) + \"    return True\") }}",
        "hints": [
          "`return` arrête **immédiatement** la fonction, même au milieu d'une boucle. Suivez l'exécution tour par tour et arrêtez-vous au premier `return` rencontré.",
          "Pour chaque appel, regardez le premier élément de la liste : quelle ligne `return` est exécutée en premier ?"
        ]
      }
    },
    {
      "uid": "NSI1-21",
      "title": "Renvoyer l'indice d'un élément, ou -1",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Parcours de liste",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname = choice([\"indice\", \"position\", \"recherche\"])\nparams = \"x, L\"\ndef fab():\n    return [randint(1, 9) for _ in range(randint(5, 8))]\ndef ind(x, L):\n    return L.index(x) if x in L else -1\ncases = []\nL = fab(); cases.append(((L[0], L), 0))\nL = fab(); cases.append(((L[-1], L), ind(L[-1], L)))\nL = fab(); x = choice(L); L = L + [x]; cases.append(((x, L), ind(x, L)))\nL = fab(); cases.append(((0, L), -1))\ncases.append(((4, []), -1))\nref = (f\"def {fname}(x, L):\\n    i = 0\\n    while i < len(L) and L[i] != x:\\n        i = i + 1\\n\"\n       f\"    if i < len(L):\\n        return i\\n    return -1\")\nex = cases[2]",
        "statement": "Écrire une fonction `{{ fname }}(x, L)` qui **renvoie** l'indice de la **première** apparition de `x` dans la liste `L`, ou `-1` si `x` n'est pas dans `L`.\n\nPar exemple, `{{ fname }}({{ repr(ex[0][0]) }}, {{ repr(ex[0][1]) }})` renvoie `{{ ex[1] }}`.\n\nContraintes : utiliser une boucle `while` ; `for`, `index` et `find` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "index",
              "find"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nLa boucle avance **tant qu'**on n'a pas trouvé `x` et qu'on reste dans la liste. On peut aussi écrire `return i` dans la boucle dès que `L[i] == x`, et `return -1` après la boucle.",
        "hints": [
          "Parcourez la liste avec un indice `i` ; dès que `L[i] == x`, la réponse est `i`.",
          "Si on sort de la boucle sans avoir trouvé `x`, il faut renvoyer `-1` : ce `return -1` est donc **après** la boucle."
        ]
      }
    },
    {
      "uid": "NSI1-22",
      "title": "Bulles : écrire contient(b, x, y)",
      "chapter": "Python : dictionnaires",
      "difficulty": 2,
      "skills": [
        "Dictionnaires : accès et modification",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname, params = \"contient\", \"b, x, y\"\ndef bulle(x, y, t):\n    return {\"x\": x, \"y\": y, \"vx\": randint(-3, 3), \"vy\": randint(-3, 3), \"taille\": t}\ncx, cy, t = randint(50, 300), randint(50, 300), randint(10, 40)\nb = bulle(cx, cy, t)\ndef dedans(b, x, y):\n    return (x - b[\"x\"]) ** 2 + (y - b[\"y\"]) ** 2 <= b[\"taille\"] ** 2\nb2 = bulle(randint(50, 300), randint(50, 300), 5)\ncases = [((b, cx, cy), True), ((b, cx + t - 1, cy), True), ((b, cx, cy + t + 2), False),\n         ((b, cx + t, cy + t), False), ((b2, b2[\"x\"] + 3, b2[\"y\"] - 4), True), ((b2, b2[\"x\"] + 4, b2[\"y\"] + 4), False)]\nref = f\"def contient(b, x, y):\\n    return (x - b['x']) ** 2 + (y - b['y']) ** 2 <= b['taille'] ** 2\"",
        "statement": "Dans un jeu, une **bulle** est un disque représenté par un dictionnaire, par exemple :\n\n{{ code_block(\"b = \" + repr(b)) }}\n\n`\"x\"` et `\"y\"` sont les coordonnées du centre, `\"vx\"` et `\"vy\"` la vitesse, `\"taille\"` le rayon.\n\nÉcrire une fonction `contient(b, x, y)` qui renvoie `True` si le point de coordonnées `(x, y)` est dans la bulle `b` (bord compris), `False` sinon.\n\nRappel : le point est dans la bulle si sa distance au centre est inférieure ou égale au rayon, c'est-à-dire si (x − xc)² + (y − yc)² ≤ taille², où (xc, yc) est le centre de la bulle.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}"
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn lit le centre et le rayon dans le dictionnaire avec `b['x']`, `b['y']` et `b['taille']`, puis on compare les carrés (pas besoin de racine carrée).",
        "hints": [
          "Les coordonnées du centre se lisent dans le dictionnaire : `b['x']` et `b['y']` ; le rayon est `b['taille']`.",
          "Une comparaison donne déjà `True` ou `False` : on peut écrire directement `return (x - b['x']) ** 2 + ... <= b['taille'] ** 2`."
        ]
      }
    },
    {
      "uid": "NSI1-23",
      "title": "Bulles : quelle bulle est touchée ?",
      "chapter": "Python : listes et chaînes",
      "difficulty": 3,
      "skills": [
        "Boucle while",
        "Données imbriquées : liste de dictionnaires",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname, params = \"bulle_touchee\", \"L, x, y\"\ndef joli_liste(L, nom):\n    return nom + \" = [\\n\" + \"\\n\".join(f\"    {e!r},\" for e in L) + \"\\n]\"\ndef bulle(x, y, t):\n    return {\"x\": x, \"y\": y, \"vx\": randint(-3, 3), \"vy\": randint(-3, 3), \"taille\": t}\ndef dedans(b, x, y):\n    return (x - b[\"x\"]) ** 2 + (y - b[\"y\"]) ** 2 <= b[\"taille\"] ** 2\ndef touchee(L, x, y):\n    i = 0\n    while i < len(L):\n        if dedans(L[i], x, y):\n            return i\n        i = i + 1\n    return -1\nL = [bulle(60 + 100 * k, randint(50, 200), randint(15, 30)) for k in range(4)]\nL = shuffled(L)\ncases = []\nk = randint(0, 3)\ncases.append(((L, L[k][\"x\"], L[k][\"y\"]), k))\nk2 = randint(0, 3)\ncases.append(((L, L[k2][\"x\"] + 5, L[k2][\"y\"] - 5), k2))\ncases.append(((L, 0, 400), -1))\n# deux bulles superposées : on renvoie la première\nL2 = [bulle(100, 100, 20), bulle(200, 200, 30), bulle(205, 205, 30)]\ncases.append(((L2, 210, 210), 1))\ncases.append((([], 10, 10), -1))\nref = (\"def contient(b, x, y):\\n    return (x - b['x']) ** 2 + (y - b['y']) ** 2 <= b['taille'] ** 2\\n\\n\"\n       \"def bulle_touchee(L, x, y):\\n    i = 0\\n    while i < len(L):\\n        if contient(L[i], x, y):\\n\"\n       \"            return i\\n        i = i + 1\\n    return -1\")",
        "statement": "Une bulle est un dictionnaire `{\"x\": ..., \"y\": ..., \"vx\": ..., \"vy\": ..., \"taille\": ...}` et la liste `L` contient toutes les bulles du jeu. La fonction `contient(b, x, y)` est déjà écrite (elle est dans le code de départ).\n\nÉcrire une fonction `bulle_touchee(L, x, y)` qui renvoie l'**indice** de la première bulle de `L` qui contient le point `(x, y)`, ou `-1` si aucune bulle ne le contient. On pourra ensuite retirer la bulle touchée avec `L.pop(i)`.\n\nPar exemple, avec\n\n{{ code_block(joli_liste(L, \"L\")) }}\n\nl'appel `bulle_touchee(L, {{ cases[1][0][1] }}, {{ cases[1][0][2] }})` renvoie `{{ cases[1][1] }}`, et `bulle_touchee(L, 0, 400)` renvoie `-1`.\n\nContrainte : utiliser une boucle `while` (pas de `for`).",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def contient(b, x, y):\n    return (x - b['x']) ** 2 + (y - b['y']) ** 2 <= b['taille'] ** 2\n\ndef bulle_touchee(L, x, y):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn parcourt les bulles avec un indice ; dès qu'une bulle contient le point, on renvoie son indice. Si la boucle se termine sans rien trouver, on renvoie `-1`.",
        "hints": [
          "Utilisez la fonction `contient` : `contient(L[i], x, y)` vaut `True` si la bulle d'indice `i` contient le point.",
          "On renvoie `i` dès qu'on trouve ; le `return -1` est **après** la boucle (aucune bulle trouvée)."
        ]
      }
    },
    {
      "uid": "NSI1-24",
      "title": "stats_voyelles : compter les voyelles dans un dictionnaire",
      "chapter": "Python : dictionnaires",
      "difficulty": 3,
      "skills": [
        "Boucle while",
        "Dictionnaires : accès et modification",
        "Compter des occurrences",
        "Écrire une fonction"
      ],
      "template": {
        "code": "fname, params = \"stats_voyelles\", \"ch\"\nMOTS = [\"informatique\", \"dictionnaire\", \"algorithme\", \"python\", \"boucle\", \"variable\", \"fonction\", \"bonjour\",\n        \"ordinateur\", \"programmation\", \"anticonstitutionnellement\", \"ecran\", \"souris\", \"clavier\", \"processeur\", \"yoyo\"]\ndef stats(ch):\n    d = {v: 0 for v in \"aeiouy\"}\n    for c in ch:\n        if c in d:\n            d[c] = d[c] + 1\n    return d\nmots = sample(MOTS, 4)\ncases = [((m,), stats(m)) for m in mots] + [((\"\",), stats(\"\")), ((\"bzz\",), stats(\"bzz\"))]\nref = (\"def stats_voyelles(ch):\\n    d = {'a': 0, 'e': 0, 'i': 0, 'o': 0, 'u': 0, 'y': 0}\\n    i = 0\\n\"\n       \"    while i < len(ch):\\n        if ch[i] in d:\\n            d[ch[i]] = d[ch[i]] + 1\\n        i = i + 1\\n    return d\")\nex = cases[0]",
        "statement": "Écrire une fonction `stats_voyelles(ch)` qui reçoit une chaîne `ch` en minuscules, sans accents, et **renvoie** un dictionnaire dont les clés sont les six voyelles `'a'`, `'e'`, `'i'`, `'o'`, `'u'`, `'y'` et les valeurs leur nombre d'apparitions dans `ch` (0 si la voyelle n'apparaît pas).\n\nPar exemple, `stats_voyelles({{ repr(ex[0][0]) }})` renvoie `{{ repr(ex[1]) }}`.\n\nContraintes : utiliser une boucle `while` ; `for` et `count` sont interdits.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for",
              "count"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn prépare le dictionnaire avec toutes les voyelles à 0, puis on parcourt la chaîne caractère par caractère : `ch[i] in d` teste si le caractère est une clé, c'est-à-dire une voyelle.",
        "hints": [
          "Commencez par créer le dictionnaire `d = {'a': 0, 'e': 0, ...}` avec les six voyelles à 0. Une chaîne se parcourt comme une liste : `ch[i]` est le caractère d'indice `i`.",
          "Pour chaque caractère `c = ch[i]` : si `c in d` (c'est une voyelle), on augmente `d[c]` de 1. On renvoie `d` après la boucle."
        ]
      }
    },
    {
      "uid": "NSI1-25",
      "title": "Construire une liste avec append dans une boucle while",
      "chapter": "Python : listes et chaînes",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Parcours de liste",
        "Écrire une fonction"
      ],
      "template": {
        "code": "variante = choice([\"pairs\", \"doubles\", \"superieurs\"])\nif variante == \"pairs\":\n    fname, params, texte = \"pairs\", \"L\", \"la liste des éléments **pairs** de `L`, dans le même ordre\"\n    corps = \"        if L[i] % 2 == 0:\\n            R.append(L[i])\\n\"\n    f = lambda L: [x for x in L if x % 2 == 0]\nelif variante == \"doubles\":\n    fname, params, texte = \"doubles\", \"L\", \"la liste des **doubles** des éléments de `L` (même ordre)\"\n    corps = \"        R.append(2 * L[i])\\n\"\n    f = lambda L: [2 * x for x in L]\nelse:\n    fname, params, texte = \"superieurs\", \"L, n\", \"la liste des éléments de `L` **strictement supérieurs** à `n`, dans le même ordre\"\n    corps = \"        if L[i] > n:\\n            R.append(L[i])\\n\"\nseuil = randint(8, 15)\ncases = []\nfor k in (5, 6, 7):\n    L = randlist(k, 1, 25)\n    if variante == \"superieurs\":\n        cases.append(((L, seuil), [x for x in L if x > seuil]))\n    else:\n        cases.append(((L,), f(L)))\ncases.append((([], seuil) if variante == \"superieurs\" else ([],), []))\nref = f\"def {fname}({params}):\\n    R = []\\n    i = 0\\n    while i < len(L):\\n{corps}        i = i + 1\\n    return R\"\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui **renvoie** {{ texte }}. La liste `L` ne doit pas être modifiée.\n\nPar exemple, `{{ fname }}({{ \", \".join(repr(a) for a in ex[0]) }})` renvoie `{{ repr(ex[1]) }}`.\n\nContraintes : utiliser une boucle `while` et `append` ; `for` (y compris dans une liste en compréhension) est interdit.",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "import re\n_code = re.sub(r\"#.*\", \"\", student_code)\nboucle_ok = False\nif re.search(r\"\\bfor\\b\", _code):\n    check(False, \"Dans cet exercice, les boucles s'écrivent avec `while` (pas de `for`, même dans une liste en compréhension).\")\nelif not re.search(r\"\\bwhile\\b\", _code):\n    check(False, \"Utilisez une boucle `while`.\")\nelse:\n    boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "for"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nOn part d'une liste vide `R = []` et on y ajoute les éléments voulus avec `R.append(...)` au fil du parcours.",
        "hints": [
          "Créez une nouvelle liste vide `R = []` avant la boucle, et renvoyez-la après la boucle.",
          "Dans la boucle, `R.append(valeur)` ajoute une valeur à la fin de `R`. Ne modifiez pas `L` (pas de `L.append` ni de `L.pop`)."
        ]
      }
    },
    {
      "uid": "NSI1-26",
      "title": "Fonction avec while : que renvoie-t-elle ?",
      "chapter": "Python : fonctions",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Fonctions : appel et valeur renvoyée",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "fname = choice([\"mys\", \"mystere\", \"f\", \"calcul\"])\nk = choice([3, 4, 5, 6, 7])\nop = choice([\">\", \">=\"])\nsrc_f = f\"def {fname}(x):\\n    a = x\\n    while a {op} {k}:\\n        a = a - {k}\\n    return a\"\nn = randint(2 * k + 1, 6 * k)\nm = randint(k + 1, 4 * k)\nappel = choice([f\"{fname}({fname}({n}))\", f\"{fname}({n}) + {fname}({m})\", f\"{fname}({n} + {fname}({m}))\", f\"{fname}({n}) * {fname}({m})\"])\nsrc = src_f + f\"\\n\\nprint({appel})\"\nrep = int(run(src))\nv_n = evaluate(src_f, f\"{fname}({n})\")",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Valeur affichée",
            "answer": "rep"
          }
        ],
        "solution": "Le programme affiche **{{ rep }}**.\n\nPar exemple `{{ fname }}({{ n }})` : `a` part de {{ n }} et diminue de {{ k }} tant que `a {{ op }} {{ k }}` ; on obtient {{ v_n }}. Pour un appel imbriqué, on calcule d'abord l'appel **intérieur**.",
        "hints": [
          "Calculez d'abord `{{ fname }}({{ n }})` à la main : écrivez les valeurs successives de `a` et arrêtez-vous quand la condition `a {{ op }} {{ k }}` devient fausse.",
          "Dans `{{ fname }}({{ fname }}(...))` ou `{{ fname }}(... + {{ fname }}(...))`, on évalue d'abord l'appel le plus à l'intérieur, puis on utilise son résultat."
        ]
      }
    },
    {
      "uid": "NSI1-27",
      "title": "Tableau de suivi d'une fonction avec while",
      "chapter": "Python : fonctions",
      "difficulty": 2,
      "skills": [
        "Boucle while",
        "Tracer l'exécution d'un programme",
        "Fonctions : appel et valeur renvoyée"
      ],
      "template": {
        "code": "fname = choice([\"mystere\", \"secret\", \"calcul\"])\nt = 3\ninit, maj = choice([\n    (\"0\", \"r = r + n * i\"),\n    (\"n\", \"r = r * 2 + i\"),\n    (\"1\", \"r = r * n - i\"),\n    (\"n\", \"r = r + i * i\"),\n    (\"0\", \"r = r + n - i\"),\n])\nn = randint(2, 6)\nsrc = f\"def {fname}(n):\\n    r = {init}\\n    i = 0\\n    while i < {t}:\\n        {maj}\\n        i = i + 1\\n    return r\"\nr = eval(init, {\"n\": n})\netapes = []\ni = 0\nwhile i < t:\n    r = eval(maj.split(\" = \")[1], {\"r\": r, \"n\": n, \"i\": i})\n    i = i + 1\n    etapes.append(r)\nfin_i = i",
        "statement": "On considère la fonction suivante :\n\n{{ code_block(src) }}\n\nOn appelle `{{ fname }}({{ n }})`. Compléter le suivi des variables (valeurs **à la fin** de chaque tour de boucle).",
        "fields": [
          {
            "type": "number",
            "label": "`r` à la fin du 1er tour",
            "answer": "etapes[0]"
          },
          {
            "type": "number",
            "label": "`r` à la fin du 2e tour",
            "answer": "etapes[1]"
          },
          {
            "type": "number",
            "label": "`r` à la fin du 3e tour",
            "answer": "etapes[2]"
          },
          {
            "type": "number",
            "label": "`i` à la sortie de la boucle",
            "answer": "fin_i"
          },
          {
            "type": "number",
            "label": "valeur renvoyée par `{{ fname }}({{ n }})`",
            "answer": "etapes[-1]"
          }
        ],
        "solution": "| tour | `i` au début du tour | `r` à la fin du tour |\n|---|---|---|\n| 1 | 0 | {{ etapes[0] }} |\n| 2 | 1 | {{ etapes[1] }} |\n| 3 | 2 | {{ etapes[2] }} |\n\nEnsuite `i` vaut {{ fin_i }}, la condition `i < {{ t }}` est fausse : la boucle s'arrête et la fonction renvoie {{ etapes[-1] }}.",
        "hints": [
          "Au départ, `n` vaut {{ n }}, `r` vaut `{{ init }}` et `i` vaut 0. Dans chaque tour, `r` est calculé avec la valeur de `i` **avant** `i = i + 1`.",
          "Quand `i` atteint {{ t }}, la condition `i < {{ t }}` est fausse : il y a donc exactement {{ t }} tours, et la fonction renvoie la dernière valeur de `r`."
        ]
      }
    },
    {
      "uid": "NSI1-28",
      "title": "Portée des variables, print et return",
      "chapter": "Python : fonctions",
      "difficulty": 2,
      "skills": [
        "Fonctions : portée des variables",
        "Fonctions : appel et valeur renvoyée"
      ],
      "template": {
        "code": "fname = choice([\"calcul\", \"max2\", \"mystere\", \"triple\"])\nk = randint(2, 5)\nn = randint(3, 9)\na, b = sample(range(2, 20), 2)\nv = n * k\nscenario = choice([\"locale\", \"globale\", \"print\", \"max2\"])\nif scenario == \"locale\":\n    src = f\"def {fname}(x):\\n    resultat = x * {k}\\n    return resultat\\n\\n{fname}({n})\\nprint(resultat)\"\n    bonne = \"Une erreur `NameError` : `resultat` n'existe pas en dehors de la fonction\"\n    expl = \"`resultat` est une variable **locale** : elle n'existe que pendant l'exécution de la fonction. Pour récupérer la valeur, il faut écrire `resultat = \" + fname + f\"({n})` avant le `print`.\"\nelif scenario == \"globale\":\n    src = f\"resultat = 0\\n\\ndef {fname}(x):\\n    resultat = x * {k}\\n    return resultat\\n\\n{fname}({n})\\nprint(resultat)\"\n    bonne = \"`0`\"\n    expl = f\"Dans la fonction, `resultat = ...` crée une variable **locale** qui porte le même nom ; la variable `resultat` du programme principal n'est pas modifiée et vaut toujours 0. La valeur renvoyée ({v}) n'est pas récupérée.\"\nelif scenario == \"print\":\n    src = f\"def {fname}(x):\\n    print(x * {k})\\n\\ny = {fname}({n})\\nprint(y)\"\n    bonne = f\"`{v}` puis `None`\"\n    expl = f\"La fonction **affiche** {v} mais ne **renvoie** rien : sans `return`, elle renvoie `None`, donc `y` vaut `None`.\"\nelse:\n    src = f\"def max2(a, b):\\n    if a > b:\\n        m = a\\n    else:\\n        m = b\\n    return m\\n\\nprint(max2({a}, {b}))\\nprint(m)\"\n    bonne = f\"`{max(a, b)}` puis une erreur `NameError` : `m` n'existe pas en dehors de la fonction\"\n    expl = \"Le premier `print` affiche la valeur renvoyée. Mais `m` est une variable **locale** de `max2` : en dehors de la fonction, elle n'existe pas.\"\nmx = max(a, b)\nerreur_res = \"Une erreur `NameError` : `resultat` n'existe pas en dehors de la fonction\"\npieges = {\n    \"locale\": [f\"`{v}`\", \"`None`\", \"`0`\", \"Rien du tout\"],\n    \"globale\": [f\"`{v}`\", erreur_res, \"`None`\"],\n    \"print\": [f\"`{v}`\", f\"`{v}` puis `{v}`\", \"`None`\", \"Rien du tout\"],\n    \"max2\": [f\"`{mx}` puis `{mx}`\", f\"`{mx}` puis `None`\", \"Une erreur `NameError` tout de suite, sans rien afficher\"],\n}[scenario]\noptions = [(bonne, True)] + [(t, False) for t in sample(pieges, 3)]",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "choice",
            "label": "",
            "options": "options"
          }
        ],
        "solution": "Réponse : {{ bonne }}.\n\n{{ expl }}",
        "hints": [
          "Une variable créée **dans** une fonction est locale : elle disparaît quand la fonction se termine, et elle est différente d'une variable du même nom à l'extérieur.",
          "`print` affiche une valeur à l'écran ; `return` la renvoie au programme qui a appelé la fonction. Une fonction sans `return` renvoie `None`."
        ],
        "max_tries": 2
      }
    },
    {
      "uid": "NSI1-29",
      "title": "Écrire une fonction simple",
      "chapter": "Python : fonctions",
      "difficulty": 1,
      "skills": [
        "Écrire une fonction",
        "Fonctions : appel et valeur renvoyée"
      ],
      "template": {
        "code": "modeles = [\n    (\"max2\", \"a, b\", \"le plus grand des deux nombres `a` et `b`\",\n     \"def max2(a, b):\\n    if a > b:\\n        return a\\n    return b\",\n     lambda: [((x, y), max(x, y)) for x, y in [sample(range(-20, 50), 2) for _ in range(3)]] + [((7, 7), 7)], [\"max\"]),\n    (\"est_pair\", \"n\", \"`True` si l'entier `n` est pair, `False` sinon\",\n     \"def est_pair(n):\\n    return n % 2 == 0\",\n     lambda: [((x,), x % 2 == 0) for x in sample(range(-30, 100), 5)] + [((0,), True)], []),\n    (\"prix_ttc\", \"prix_ht\", \"le prix TTC correspondant au prix hors taxes `prix_ht`, avec une TVA de 20 %\",\n     \"def prix_ttc(prix_ht):\\n    return prix_ht * 1.2\",\n     lambda: [((x,), x * 1.2) for x in sample(range(1, 500), 4)] + [((0,), 0)], []),\n    (\"moyenne3\", \"a, b, c\", \"la moyenne des trois nombres `a`, `b` et `c`\",\n     \"def moyenne3(a, b, c):\\n    return (a + b + c) / 3\",\n     lambda: [((x, y, z), (x + y + z) / 3) for x, y, z in [sample(range(0, 21), 3) for _ in range(4)]], [\"sum\"]),\n    (\"valeur_absolue\", \"x\", \"la valeur absolue du nombre `x` (`x` s'il est positif, `-x` sinon)\",\n     \"def valeur_absolue(x):\\n    if x < 0:\\n        return -x\\n    return x\",\n     lambda: [((x,), abs(x)) for x in sample(range(-50, 50), 5)] + [((0,), 0)], [\"abs\"]),\n    (\"en_secondes\", \"h, m, s\", \"la durée `h` heures `m` minutes `s` secondes convertie en secondes\",\n     \"def en_secondes(h, m, s):\\n    return h * 3600 + m * 60 + s\",\n     lambda: [((h, m, s), h * 3600 + m * 60 + s) for h, m, s in [(randint(0, 5), randint(0, 59), randint(0, 59)) for _ in range(4)]], []),\n    (\"est_majeur\", \"age\", \"`True` si `age` est supérieur ou égal à 18, `False` sinon\",\n     \"def est_majeur(age):\\n    return age >= 18\",\n     lambda: [((17,), False), ((18,), True), ((randint(19, 80),), True), ((randint(0, 16),), False)], []),\n]\nfname, params, texte, ref, fab, interdits = choice(modeles)\ncases = fab()\nex = cases[0]",
        "statement": "Écrire une fonction `{{ fname }}({{ params }})` qui **renvoie** {{ texte }}.\n\nPar exemple, `{{ fname }}({{ \", \".join(repr(a) for a in ex[0]) }})` renvoie `{{ repr(ex[1]) }}`.\n{{ \"\" if not interdits else chr(10) + \"Contrainte : \" + \", \".join(\"`\" + i + \"`\" for i in interdits) + \" interdit.\" }}",
        "fields": [
          {
            "type": "code",
            "label": "Votre fonction",
            "starter": "def {{ fname }}({{ params }}):\n    ",
            "tests": "boucle_ok = True\nimport copy\nfn = student.get(fname)\nif not boucle_ok:\n    pass  # consigne « while » non respectée : la fonction n'est pas testée\nelif not callable(fn):\n    check(False, f\"la fonction {fname} doit être définie\")\nelse:\n    for args, attendu in cases:\n        appel = fname + \"(\" + \", \".join(repr(a) for a in args) + \")\"\n        try:\n            obtenu = fn(*copy.deepcopy(args))\n        except Exception as e:\n            if type(e).__name__ == \"TimeLimit\":\n                raise\n            check(False, f\"`{appel}` provoque une erreur : {erreur(e)}\")\n            continue\n        check_equal(obtenu, attendu, f\"`{appel}` renvoie `{obtenu!r}` au lieu de `{attendu!r}`\")",
            "reference": "{{ ref }}",
            "forbid": [
              "max",
              "abs"
            ]
          }
        ],
        "solution": "{{ code_block(ref) }}\n\nUne fonction reçoit des **paramètres**, fait un calcul et **renvoie** le résultat avec `return` (et non `print`).",
        "hints": [
          "La première ligne est déjà écrite : `def {{ fname }}({{ params }}):`. Le corps de la fonction est indenté et se termine par `return ...`.",
          "Utilisez `return` et non `print` : la fonction est testée sur le résultat qu'elle **renvoie**. Testez-la sur l'exemple de l'énoncé."
        ]
      }
    },
    {
      "uid": "NSI1-30",
      "title": "Fonction avec paramètres et if : que renvoie-t-elle ?",
      "chapter": "Python : fonctions",
      "difficulty": 1,
      "skills": [
        "Fonctions : appel et valeur renvoyée",
        "Conditions if/elif/else",
        "Tracer l'exécution d'un programme"
      ],
      "template": {
        "code": "fname = choice(NOMS_FONCTIONS)\nk = randint(2, 4)\ncorps = choice([\n    f\"    if a > b:\\n        return a - b\\n    return b * {k}\",\n    f\"    if a % 2 == 0:\\n        return a + b\\n    return a * b\",\n    f\"    if a < b:\\n        a = a + {k}\\n    return a - b\",\n    f\"    c = a * {k}\\n    if c > b:\\n        return c - b\\n    return b\",\n])\nx, y = sample(range(1, 12), 2)\nappel = choice([f\"{fname}({x}, {y}) + {fname}({y}, {x})\", f\"{fname}({x}, {y}) * 2\", f\"{fname}({fname}({x}, {y}), {y})\"])\nsrc = f\"def {fname}(a, b):\\n{corps}\\n\\nprint({appel})\"\nrep = int(run(src))",
        "statement": "Qu'affiche ce programme ?\n\n{{ code_block(src) }}",
        "fields": [
          {
            "type": "number",
            "label": "Valeur affichée",
            "answer": "rep"
          }
        ],
        "solution": "Le programme affiche **{{ rep }}**.\n\nÀ chaque appel, `a` et `b` prennent les valeurs données **dans l'ordre** des parenthèses ; `return` arrête la fonction et renvoie la valeur.",
        "hints": [
          "Traitez chaque appel séparément : écrivez `a = ...` et `b = ...`, puis suivez le code de la fonction jusqu'au premier `return`.",
          "Attention à l'ordre des arguments : dans `{{ fname }}({{ y }}, {{ x }})`, c'est `a` qui vaut {{ y }}."
        ]
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
