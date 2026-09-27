# Format des questions

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

## 1. Le générateur (`code`)

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

## 2. Énoncé, intitulés, correction

Markdown (sous-ensemble) : paragraphes, `**gras**`, `*italique*`, `` `code` ``, blocs
```` ```python ````, listes, citations `>`, tableaux `| a | b |`, titres, liens.
`{{ expression }}` est remplacé par la valeur de l'expression Python (les flottants entiers
s'affichent sans `.0`).

## 3. Champs de réponse (`fields`)

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

## 3 bis. Essais et indices

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

## 4. Variété et « jamais deux fois la même question »

* L'empreinte d'une instance est le SHA-256 (16 premiers caractères hexadécimaux) du JSON
  canonique de sa partie publique (énoncé + champs, clés triées).
* Au moment de servir une question, le serveur évite les empreintes **déjà vues par cet élève**
  et celles **servies à n'importe qui dans les 3 dernières heures** (deux voisins n'ont pas les
  mêmes données) : jusqu'à 25 graines sont essayées.
* L'éditeur indique combien d'énoncés différents apparaissent sur 30 tirages. Pour une
  question « écrire une fonction », l'énoncé peut rester identique : ce sont les tests cachés
  qui changent.

## 5. Protocole du moteur (pour réutiliser le moteur depuis une autre stack)

Le moteur (`engine/`) est un programme autonome : une requête JSON sur l'entrée standard,
une réponse JSON sur la sortie standard.

```sh
echo '{"action":"generate","template":{...},"seed":42,"avoid":[]}' | \
  python3 -I -c "import sys; sys.path.insert(0, '/chemin/questionnapp'); from engine.runner import main; main()"
```

| action | entrée | résultat (`{"ok": true, "result": ...}`) |
|---|---|---|
| `generate` | `template`, `seed`, `avoid` (empreintes), `max_tries` | `{seed, fingerprint, public: {statement, fields}, fresh}` |
| `preview` | `template`, `seed` | idem + `expected` (réponses affichables), `solution`, `variety`, `deterministic` |
| `selftest` | `template`, `samples` | `{status: ok \| warning \| error, samples, distinct, errors, warnings}` : génération sur plusieurs graines, variété, réponse de référence acceptée, tests de code non triviaux |
| `check` | `template`, `seed`, `answers` | `{score, correct, fields: [{score, correct, feedback, expected}], solution, hints, max_tries, fingerprint}` |

Erreur : `{"ok": false, "error": "...", "where": "code" | "statement" | "fields[0].answer"…, "line": 3}`.

Réponses (`answers`) : une valeur par champ — chaîne pour `number`/`text`/`code`/`sql`,
indice (entier) ou liste d'indices pour `choice` (indices dans l'ordre **affiché**).
