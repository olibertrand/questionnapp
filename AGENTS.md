# AGENTS.md — Brief de ce projet

## Le projet
- Ce que fait le produit : une appli de questionnaires, alternative à WIMS. Chaque fois que la
  même question est posée (à la même personne ou à un autre utilisateur), les données sont
  différentes. Il s'agit avant tout de poser des questions sur la programmation Python,
  l'algorithmique et d'autres chapitres d'informatique comme l'architecture ou les bases de
  données.
- Pour qui : un seul professeur (moi) pour l'instant ; des élèves de Seconde SNT, de Première
  NSI et de Terminale NSI.
- Ce que je ne veux jamais casser :
  - les réponses et les statistiques des élèves ;
  - la connexion des élèves ;
  - la correction automatique ;
  - l'isolement du code tapé par les élèves (bac à sable) ;
  - le tirage aléatoire des données : chaque élève, et chaque nouvel essai, reçoit le même
    exercice avec des valeurs différentes.

## Langue
- On se parle en français. L'interface et les questions sont en français.
- Dans le code : noms de variables, de fonctions et de fichiers en anglais ; commentaires en
  français (c'est l'existant, on le garde).
- Sur le dépôt : messages de commit, demandes de fusion (pull requests) et documentation en
  français.
- À reconsidérer seulement si le projet s'ouvre à des contributeurs non francophones.

## Comment je veux qu'on travaille
- Applique les meilleures pratiques par défaut, même si je ne les demande pas.
- Va droit au but : pas de cours non demandé. Mais **signale chaque action** (fichier modifié,
  commit, branche, demande de fusion…) et explique-la en une phrase simple, sans jargon ; un mot
  technique inévitable reçoit une courte définition.
- Présente ton plan et attends mon accord pour les chantiers qui touchent à « ce que je ne veux
  jamais casser » (voir plus haut). Pour le reste, avance.
- Quand une tâche est finie, dis-moi précisément quoi tester à la main, comme un utilisateur
  (prof ou élève).
- Commits au format *conventional commits*, message en français : `feat:` (nouveauté), `fix:`
  (correction), `refactor:`, `docs:`, `chore:`, `feat!:` ou `BREAKING CHANGE:` (changement
  incompatible). Exemple : `feat: séances thématiques pour certains élèves`. Je n'en écris
  jamais moi-même : c'est ton travail, à chaque fois.
- Circuit de mise en ligne : tu travailles sur une branche, tu ouvres une demande de fusion vers
  `main`, je la relis et je la fusionne, puis je fais `git pull` et je redémarre l'appli sur le
  serveur. Tu ne pousses jamais directement sur `main` et tu ne fusionnes jamais toi-même.
- Des élèves utilisent l'appli en classe : une mise à jour ne doit jamais rendre la base
  existante inutilisable (les migrations sont automatiques et sans perte de données).

## RÈGLE VIVANTE
Chaque fois qu'une ligne de ce fichier me gêne à l'usage — trop de questions, pas assez, du
jargon, des explications inutiles — je te demande de la modifier ici, et tu t'y tiens ensuite.
Quand je corrige une de tes habitudes, propose de noter la préférence ici. Ce brief s'ajuste à
moi, pas l'inverse. N'inscris jamais de secret (mot de passe, clé, adresse de serveur) dans ce
fichier.

## Garde-fous — demande-moi TOUJOURS avant de :
- toucher à la connexion, aux comptes ou aux mots de passe ;
- supprimer ou modifier en masse des données existantes (réponses, statistiques, questions déjà
  utilisées), changer la structure de la base de données, ou faire une action irréversible ;
- modifier la correction automatique, l'isolement du code élève ou le tirage aléatoire des
  données ;
- ajouter un service externe (par exemple l'IA intégrée à l'appli) ou une dépendance importante
  (aujourd'hui : uniquement la bibliothèque standard de Python, rien à installer) ;
- mettre quoi que ce soit sur `main` sans passer par une demande de fusion que je valide.
Dans ces cas : explique-moi le risque en langage simple, propose, et attends que je valide.

## La ligne rouge — sécurité non négociable (rappelle-la-toi à chaque fois)
Ce produit doit, en permanence, respecter ces règles. Si tu vois que l'une d'elles est violée,
préviens-moi immédiatement.
1. Tout ce qui circule entre les utilisateurs et le produit est chiffré (HTTPS, assuré par le
   proxy du serveur ; cookies sécurisés avec `QUESTIONNAPP_SECURE_COOKIES=1`).
2. Les mots de passe des utilisateurs ne sont jamais lisibles par personne, même moi (stockés
   hachés avec scrypt).
3. Personne ne peut parler directement à la base de données (requêtes SQL toujours
   paramétrées, jamais construites avec du texte venant d'un utilisateur).
4. Chaque utilisateur ne voit et ne modifie QUE ses propres données — même en trichant sur un
   identifiant dans l'URL. Un professeur ne voit que ses classes et leurs élèves.
5. Les clés d'accès (par exemple une future clé d'IA) ne partent jamais vers le navigateur.
6. Chaque action a une limite de fréquence (personne ne peut se servir en boucle).
7. Les sauvegardes de la base (le fichier SQLite) existent et ont été testées au moins une fois.
8. Rien de ce qui servait à tester ne reste ouvert en production : jamais `scripts/demo.py`
   sur le serveur, pas de compte de démo (admin/admin, prof/prof, eleve01…).
9. Le code tapé par les élèves s'exécute isolé (sous-processus, limites de temps et de mémoire,
   pas d'accès aux fichiers, au réseau ni aux réponses attendues) ; aucune modification ne doit
   affaiblir cet isolement.

## Repères techniques
- Python 3.11+, bibliothèque standard uniquement ; base SQLite ; interface en JavaScript sans
  framework. Lancement : `python3 run.py`.
- Découpage : `app/` (serveur et API), `engine/` (moteur de questions, exécuté à part),
  `web/` (interface), `banque/` (questions, un fichier JSON par thème), `docs/` (API, format
  des questions, architecture), `claude-projet/` (projet Claude pour créer des questions).
- Avant toute demande de fusion : `python3 -m unittest discover tests` doit passer, et
  `python3 scripts/build_claude_project.py --check` aussi (sinon le régénérer sans l'option).
- Toute question de `banque/` doit passer l'auto-test du moteur et avoir un identifiant `uid`
  unique (`DICO-21`…) ; un import ne doit jamais créer de doublon.
- Pour vérifier une modification de l'interface, la tester dans un vrai navigateur.

## Conventions et décisions prises
- Pas de dépendance externe : tout fonctionne avec Python seul, pour rester facile à installer
  et portable vers une autre technologie (contrats documentés dans `docs/`).
- Les questions sont des modèles écrits en Python (format : `docs/QUESTION_FORMAT.md`) ;
  plusieurs essais avec indices avant d'afficher la solution ; score retenu 100/75/50 %.
- Les questions vivent dans `banque/` ; la base de l'appli reste la version de travail.
- Les nouvelles questions se créent avec le projet Claude (`claude-projet/`), puis s'importent ;
  l'import refait un auto-test de chaque question.
- La version en cours (commit) s'affiche en bas de chaque page de l'appli.

## Où on en est
- L'appli est en production sur mon serveur et des élèves l'utilisent déjà.
- Prochaine étape qui m'importe : la création de nouvelles questions.
- Proposé, pas encore décidé : vérification automatique des tests sur GitHub à chaque demande de
  fusion ; protection de la branche `main` sur GitHub ; ne faire confiance à l'en-tête
  `X-Forwarded-For` que derrière le proxy ; limites de fréquence au-delà de la connexion.
