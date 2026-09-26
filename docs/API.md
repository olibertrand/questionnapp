# API REST

Toutes les routes sont sous `/api`, échangent du JSON (UTF-8) et renvoient les erreurs sous
la forme `{"error": "message lisible"}` avec un code HTTP 4xx/5xx (422 pour un modèle de
question invalide, avec en plus `where` et `line`).

* **Session** : cookie `qa_session` (HttpOnly, SameSite=Lax) posé par `POST /api/auth/login`.
* **CSRF** : toute requête autre que GET doit porter l'en-tête `X-Requested-With: questionnapp`.
* **Rôles** : `admin` (tout), `teacher` (ses classes, ses élèves, toute la banque de questions),
  `student` (son travail uniquement).
* Dates : ISO 8601 UTC (`2026-09-26T08:15:00Z`), jours au format `AAAA-MM-JJ`.
* Statistiques : filtre de période facultatif `?from=AAAA-MM-JJ&to=AAAA-MM-JJ`.

## Authentification
| Méthode | Route | Corps / réponse |
|---|---|---|
| POST | `/auth/login` | `{username, password}` → `{user}` (8 échecs / 5 min → 429) |
| POST | `/auth/logout` | |
| GET | `/auth/me` | `{user: {id, username, display_name, role} \| null}` |
| POST | `/auth/password` | `{current, new}` |

## Utilisateurs (prof : élèves seulement ; admin : tous)
| Méthode | Route | |
|---|---|---|
| GET | `/users?role=` | `{users: [{id, username, display_name, role, active, last_login_at, classes}]}` |
| POST | `/users` | `{username, password, display_name, role, class_ids}` |
| POST | `/users/import` | `{csv: "identifiant;mdp;nom\n...", class_id, role}` → `{created, errors}` |
| PATCH | `/users/:id` | `{display_name?, username?, password?, active?, role? (admin)}` |
| DELETE | `/users/:id` | |

## Classes
| Méthode | Route | |
|---|---|---|
| GET | `/classes` | classes visibles (élève : les siennes) |
| POST | `/classes` | `{name, description}` (le prof créateur en devient membre) |
| GET | `/classes/:id` | `{class: {..., members, question_ids}}` |
| PATCH / DELETE | `/classes/:id` | |
| POST | `/classes/:id/members` | `{user_ids}` |
| DELETE | `/classes/:id/members/:uid` | |
| PUT | `/classes/:id/questions` | `{question_ids}` remplace les questions affectées |
| GET | `/classes/:id/assignments` | séances de la classe |

## Chapitres et compétences
`GET/POST /chapters`, `PATCH/DELETE /chapters/:id` (`{name, position}`),
`GET /skills`, `PATCH/DELETE /skills/:id`. Les compétences sont créées à la volée depuis les questions.

## Questions (professeurs)
| Méthode | Route | |
|---|---|---|
| GET | `/questions?chapter_id=&class_id=&q=&archived=1` | liste avec compétences, classes, nb de réponses, score moyen |
| POST | `/questions` | `{title, chapter_id \| chapter_name, difficulty (1-3), skills: [noms], class_ids, template}` |
| GET | `/questions/:id` | `{question: {..., template, skills, class_ids}}` |
| PUT | `/questions/:id` | idem POST (+ `archived`) ; un modèle modifié crée une nouvelle version |
| DELETE | `/questions/:id` | supprime, ou archive si des élèves y ont répondu |
| POST | `/questions/:id/duplicate` | |
| POST | `/questions/preview` | `{template, seed?}` → réponse brute du moteur (`preview`) |
| POST | `/questions/try` | `{template, seed, answers}` → réponse brute du moteur (`check`) |
| POST | `/questions/bulk-classes` | `{question_ids, class_ids, add: bool}` |
| GET | `/questions/export?ids=1,2` | `{format: "questionnapp/questions", version: 1, questions: [...]}` |
| POST | `/questions/import` | même format (+ `class_ids`) → `{created, skipped, errors}` |
| POST | `/questions/import-examples` | `{class_ids}` : importe `examples/questions-informatique.json` (sans doublon de titre) |

## Séances
| Méthode | Route | |
|---|---|---|
| POST | `/assignments` | `{class_ids \| class_id, title, day, question_ids}` (une séance par classe) |
| GET | `/assignments/:id` | séance + avancement de chaque élève |
| PUT / DELETE | `/assignments/:id` | |

## Travail de l'élève
| Méthode | Route | |
|---|---|---|
| GET | `/me/dashboard` | séances (±45 j) avec avancement, chapitres avec maîtrise, compétences, dernières réponses, totaux |
| GET | `/me/assignments/:id` | une séance et l'avancement |
| GET | `/me/history?limit=` | réponses passées |
| POST | `/practice/next` | `{mode: "assignment", assignment_id, question_id?}` · `{mode: "chapter", chapter_id}` · `{mode: "adaptive", chapter_id?}` · `{mode: "free", question_id}` → `{attempt: {id, question, instance: {statement, fields}, context}}` ou `{done: true, progress}` |
| POST | `/attempts/:id/answer` | `{answers: [...]}` → `{result: {score, correct, fields, solution}, progress?}` (une seule correction par tentative) |
| GET | `/attempts/:id` | énoncé vu, réponses, correction (élève propriétaire ou prof) |

## Statistiques (professeurs)
| Route | Contenu |
|---|---|
| `/stats/classes/:id/overview` | synthèse, activité par jour, par élève : dernière connexion, connexions, réponses, score moyen, avancement des séances |
| `/stats/classes/:id/skills` | matrice élève × compétence `{students, groups, cells: {"uid:gid": {n, avg, mastery}}}` |
| `/stats/classes/:id/chapters` | matrice élève × chapitre (même format) |
| `/stats/classes/:id/questions` | par question : élèves, réponses, réussites, abandons, score moyen |
| `/stats/classes/:id/assignments` | matrice élève × séance |
| `/stats/students/:id` | profil, connexions, tentatives une par une, maîtrise par compétence et par chapitre |
| `/stats/classes/:id/export.csv` | toutes les réponses (séparateur `;`, UTF-8 avec BOM pour Excel) |
