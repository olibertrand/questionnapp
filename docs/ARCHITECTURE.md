# Architecture

L'objectif principal est la **portabilité** : pouvoir changer de langage ou de framework
côté serveur (ou côté client) sans tout réécrire. L'application est donc découpée en
quatre briques indépendantes, reliées par des contrats documentés.

```
 navigateur                      serveur (Python, bibliothèque standard)         sous-processus isolé
┌────────────┐   HTTP + JSON   ┌───────────────────────────────┐  JSON stdin/out  ┌──────────────────┐
│ web/ (SPA  │ ──────────────▶ │ app/ : routes, droits, stats, │ ───────────────▶ │ engine/ : génère │
│ JS natif)  │  docs/API.md    │ choix adaptatif               │ QUESTION_FORMAT  │ et corrige       │
└────────────┘                 └──────────────┬────────────────┘                  └──────────────────┘
                                              │ SQL standard (app/schema.sql)
                                              ▼
                                       SQLite (fichier)
```

| Brique | Contrat | Pour la remplacer |
|---|---|---|
| Interface `web/` | `docs/API.md` | n'importe quel front (React, Vue, appli mobile) qui parle à l'API |
| Serveur `app/` | `docs/API.md` + `app/schema.sql` | réimplémenter les routes (Django, Flask, FastAPI, Express, Symfony, Spring…) ; `tests/test_api.py` sert de test de contrat car il ne passe que par HTTP |
| Moteur `engine/` | protocole JSON (`docs/QUESTION_FORMAT.md` § 5) | se réutilise tel quel depuis n'importe quel langage (il suffit de lancer un processus Python) |
| Base | `app/schema.sql` (SQL standard) | PostgreSQL/MySQL : remplacer `INTEGER PRIMARY KEY` par `SERIAL`/`AUTO_INCREMENT`, `INSERT OR IGNORE` par `ON CONFLICT DO NOTHING` |

Aucune dépendance externe : Python ≥ 3.11 suffit (serveur `http.server`, `sqlite3`,
`hashlib.scrypt`). Le front n'a ni framework ni étape de compilation ; seule la coloration
syntaxique (highlight.js, CDN) est optionnelle.

## Pourquoi un moteur en Python ?

Les questions portent sur la programmation Python, l'algorithmique et les bases de données :
il faut pouvoir **exécuter du code** pour calculer ce qu'affiche un programme généré au
hasard, **tester le code écrit par l'élève** et **exécuter des requêtes SQL**. Écrire les
générateurs en Python (plutôt que dans un mini-langage maison comme WIMS) permet aux
professeurs d'informatique de les écrire sans rien apprendre de nouveau.

## Cycle d'une question

1. `POST /practice/next` : le serveur choisit une question (séance, chapitre ou mode adaptatif),
   tire une graine aléatoire et demande au moteur une instance en lui passant les empreintes
   à éviter. Il enregistre la tentative (graine, empreinte, énoncé tel que vu, **version** du
   modèle) et n'envoie au navigateur que la partie publique : **jamais les réponses**.
2. `POST /attempts/:id/answer` : le serveur relance le moteur avec la même graine et la même
   version du modèle ; le moteur régénère l'instance à l'identique et corrige. Tant qu'il reste
   des essais et que la réponse n'est pas juste, le serveur ne renvoie que « juste / faux », les
   commentaires et un indice (jamais la solution) et enregistre l'essai dans `history`. Sur une
   bonne réponse, au dernier essai ou sur `reveal`, la tentative est terminée : score pondéré par
   le nombre d'essais, correction complète. Pour recommencer, l'élève demande de nouvelles données.
3. Modifier une question crée une nouvelle version : les tentatives passées restent
   consultables et cohérentes.

## Mode adaptatif (`app/adaptive.py`)

* Maîtrise d'une compétence : moyenne pondérée des scores de l'élève sur les questions liées,
  poids `0,75^rang` (la réponse la plus récente pèse 1), avec un a priori de 0,5 comptant pour
  une réponse. Une compétence jamais travaillée vaut 0,5.
* Besoin d'une question = moyenne de `1 − maîtrise` sur ses compétences, + 0,25 si l'élève ne
  l'a jamais vue. Poids de tirage = `(0,05 + besoin)²`, divisé par 50 pour la question qui
  vient d'être faite et par ~3 pour les 4 dernières. On tire au hasard selon ces poids : les
  notions fragiles reviennent souvent sans que ce soit prévisible.
* Mode chapitre : parcourt toutes les questions du chapitre, les moins travaillées d'abord.

## Sécurité

* Mots de passe : scrypt (n=2¹⁴, r=8, p=1) salé. Sessions : jeton aléatoire de 256 bits,
  seul son SHA-256 est stocké. Limitation des tentatives de connexion.
* CSRF : en-tête `X-Requested-With` obligatoire sur les requêtes modifiantes + cookie SameSite=Lax.
* En-têtes : CSP stricte (pas de script en ligne), `X-Frame-Options: DENY`, `nosniff`.
* Tout le Markdown est échappé avant rendu (pas de HTML brut dans les énoncés).
* Contrôle d'accès vérifié côté serveur sur chaque route (un prof ne voit que ses classes et
  leurs élèves ; un élève que ses propres tentatives).
* **Code exécuté** (générateurs des profs, code et SQL des élèves) : sous-processus séparé,
  sans variables d'environnement, dans un dossier temporaire, avec limites CPU/mémoire,
  interdiction de créer des processus, délai maximal, et un *audit hook* Python qui bloque
  réseau, écriture et lecture de fichiers, sous-processus, `ctypes`, imports non autorisés.
  Les objets renvoyés par l'élève sont comparés sans faire confiance à leurs `__eq__`.
  Pour éviter qu'un élève lise la réponse attendue dans la mémoire du correcteur, son code
  est analysé avant exécution (attributs internes, accès à `sys`/`os`) et s'exécute avec des
  builtins et imports restreints, l'introspection des frames étant bloquée ; en SQL,
  `ATTACH` et `PRAGMA` sont refusés. Le code soumis est de toute façon conservé et visible
  par le professeur dans le suivi de l'élève.
  Ce n'est pas un bac à sable parfait : pour un serveur exposé sur Internet, isolez aussi le
  moteur au niveau système, par exemple `QUESTIONNAPP_SANDBOX_CMD="firejail --quiet --net=none --private"`
  ou en faisant tourner l'application dans un conteneur sans réseau sortant et avec un
  utilisateur dédié.

## Arborescence

```
app/            serveur : server.py (HTTP), web.py (routeur), db.py, security.py,
                adaptive.py, engine_client.py, api/*.py (une route par fichier thème), schema.sql
engine/         moteur : core.py (génération/correction), helpers.py (fonctions des modèles),
                sandbox.py (garde-fous), runner.py (protocole JSON)
web/            interface : index.html, css/, js/app.js (routeur), js/views/*.js, player.js
banque/         banques de questions, un fichier JSON par thème (format d'import/export)
claude-projet/  instructions et fichiers pour créer des questions avec un projet Claude
scripts/demo.py données de démonstration
tests/          moteur, exemples (chaque question accepte sa propre correction), API
```
