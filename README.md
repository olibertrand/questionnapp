# QuestionnApp

Plateforme d'exercices en ligne, alternative à WIMS, pensée pour l'**informatique** (Python,
algorithmique, représentation des données, architecture, bases de données) : chaque question
est un **modèle** dont les données sont tirées au hasard, si bien qu'à chaque fois (pour le
même élève ou pour son voisin) l'exercice est le même, travaille les mêmes compétences, mais
avec des valeurs différentes. La correction est automatique.

## Fonctionnalités

**Questions**
- Générateurs écrits en **Python** avec des fonctions d'aide (`randint`, `choice`, `run(code)`
  pour calculer ce qu'affiche un programme, `sql_table`, `twos`…).
- Types de réponses : **nombre**, **texte / sortie de programme**, **QCM** (simple ou multiple,
  options générées), **code Python** vérifié par des tests cachés aléatoires (avec interdiction
  de certaines fonctions), **requête SQL** comparée à une requête de référence.
- **Plusieurs essais avec indices** : après une erreur, l'élève voit ce qui est juste ou faux
  (et, pour le code, les tests qui échouent) mais pas la solution ; un indice de plus à chaque
  erreur, écrit par le prof avec les données du tirage ou générique à défaut. Score : 100 % au
  1er essai, 75 % au 2e, 50 % au 3e ; bouton « Voir la solution ».
- Éditeur avec **aperçu en direct**, test de ses propres réponses, indicateur de variété,
  erreurs localisées (ligne du générateur), modèles de départ, import/export JSON.
- Chaque question a un **identifiant** lisible et unique (`DICO-07`, `Q-0042`) ; un import ne
  réimporte jamais une question déjà présente. Suppression en bloc et suppression des doublons.
- Une question appartient à un chapitre, travaille des compétences et peut être affectée à
  0, 1 ou plusieurs classes. Chaque modification est versionnée.
- **Banques de questions** : répertoire [`banque/`](banque/LISEZMOI.md), un fichier JSON par
  thème (40 questions fournies, dont 18 sur les dictionnaires et les données imbriquées),
  consultable depuis le menu **Banques** avec aperçu, import et mise à jour.

**Utilisateurs et classes**
- Comptes administrateur, professeur, élève (identifiant / mot de passe), import de listes
  d'élèves par copier-coller depuis un tableur.
- Classes avec leurs élèves et leurs professeurs ; **groupes personnalisés** d'élèves dans une classe.
- À la première connexion (ou après une réinitialisation par un prof), chacun doit choisir son
  mot de passe (il peut garder celui qu'on lui a donné).

**Élèves** : trois façons de travailler
- les **séances** données par le prof, à toute la classe ou à certains élèves / groupes :
  séances **datées** (pour un jour donné) et séances **thématiques** (sans date, actives jusqu'à
  ce que le prof les désactive), toutes affichées en haut de la page d'accueil ;
- l'**entraînement par chapitre** (toutes les questions du chapitre, les moins vues d'abord) ;
- l'**entraînement automatique** qui repropose les notions les moins maîtrisées.

**Statistiques** (profs et admin)
- Vue d'ensemble : connexions (quand, combien), activité par jour, réponses et score moyen
  par élève, avancement des séances.
- Par **compétence** et par **chapitre** : carte de chaleur élève × notion (maîtrise pondérée
  par la récence) et synthèse de classe.
- Par **question** et par **séance**.
- Suivi individuel : connexions, chaque question traitée avec l'énoncé exact reçu, les
  réponses données et la correction.
- Filtre par période et **export CSV**.

## Démarrage

Prérequis : **Python 3.11 ou plus**, rien d'autre à installer.

```sh
python3 scripts/demo.py   # facultatif : données de démo (admin/admin, prof/prof, eleve01..12/eleve)
python3 run.py            # puis ouvrir http://127.0.0.1:8000
```

Sans les données de démo, le premier lancement crée un compte `admin` et affiche son mot de
passe dans le terminal (ou utilise `QUESTIONNAPP_ADMIN_PASSWORD`). Pour charger des questions :
menu **Banques**, choisir un thème, essayer les questions avec « Aperçu », puis importer.
Dans la page Questions, le bouton « Aperçu » montre une question comme la verra un élève, sans
qu'elle soit affectée à une classe.

Premiers pas : 1) créer une classe et y ajouter les élèves ; 2) ajouter des questions et les
affecter à la classe ; 3) éventuellement créer une séance datée. Les élèves ne voient que les
questions affectées à leurs classes.

### Configuration (variables d'environnement)

| Variable | Défaut | |
|---|---|---|
| `QUESTIONNAPP_HOST` / `QUESTIONNAPP_PORT` | `127.0.0.1` / `8000` | mettre `0.0.0.0` pour le réseau local |
| `QUESTIONNAPP_DB` | `data/questionnapp.db` | fichier SQLite |
| `QUESTIONNAPP_ADMIN_PASSWORD` | aléatoire | mot de passe du premier admin |
| `QUESTIONNAPP_SECURE_COOKIES` | `0` | `1` derrière un proxy HTTPS |
| `QUESTIONNAPP_SANDBOX_CMD` | vide | préfixe d'isolation du moteur, ex. `firejail --quiet --net=none --private` |
| `QUESTIONNAPP_SESSION_DAYS` | `7` | durée des sessions |
| `QUESTIONNAPP_BANK_DIR` | `banque/` | répertoire des banques de questions |
| `QUESTIONNAPP_BACKUP_DIR` | `data/sauvegardes/` | dossier des sauvegardes de la base |

En production : voir [`docs/MIGRATION_VPS.md`](docs/MIGRATION_VPS.md) et le dossier `deploy/`
(service systemd, site nginx, script de mise à jour). Principe : placer l'application derrière un proxy HTTPS (nginx, Caddy), activer les
cookies sécurisés et isoler le moteur (voir `docs/ARCHITECTURE.md`, § Sécurité).
Sauvegarde : copier le fichier SQLite.

## Créer des questions avec Claude

Le dossier [`claude-projet/`](claude-projet/LISEZMOI.md) permet de monter un projet Claude
(claude.ai) qui transforme un cours et ses exercices en questions : notions du chapitre et
prérequis mobilisés dans les exercices. Claude teste ses questions avec le moteur de l'app,
puis on importe le fichier JSON obtenu ; l'import refait un auto-test de chaque question.

### Sauvegardes

```sh
python3 scripts/sauvegarde.py              # copie sûre de la base, même appli en marche, avec rotation
python3 scripts/restaurer.py --test FICHIER  # vérifie une sauvegarde sans toucher à la vraie base
```

Planification chaque nuit, test et restauration : [`docs/SAUVEGARDE.md`](docs/SAUVEGARDE.md).

### Repartir d'une banque de questions vide

```sh
python3 scripts/vider_questions.py   # serveur arrêté ; garde comptes et classes, demande confirmation
```

## Tests

```sh
python3 -m unittest discover tests
```

## Documentation

- [`docs/QUESTION_FORMAT.md`](docs/QUESTION_FORMAT.md) — écrire des questions (référence complète)
- [`docs/API.md`](docs/API.md) — l'API REST (contrat entre l'interface et le serveur)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — découpage, portabilité, sécurité, algorithme adaptatif
