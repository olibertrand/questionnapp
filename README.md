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
- Éditeur avec **aperçu en direct**, test de ses propres réponses, indicateur de variété,
  erreurs localisées (ligne du générateur), modèles de départ, import/export JSON.
- Une question appartient à un chapitre, travaille des compétences et peut être affectée à
  0, 1 ou plusieurs classes. Chaque modification est versionnée.
- 20 questions d'exemple fournies (`examples/questions-informatique.json`).

**Utilisateurs et classes**
- Comptes administrateur, professeur, élève (identifiant / mot de passe), import de listes
  d'élèves par copier-coller depuis un tableur.
- Classes avec leurs élèves et leurs professeurs.

**Élèves** : trois façons de travailler
- les **séances** du jour données par le prof (et celles à venir / en retard) ;
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
passe dans le terminal (ou utilise `QUESTIONNAPP_ADMIN_PASSWORD`). Pour charger les 20 questions
d'exemple : *Questions → Ajouter les questions d'exemple* (en cochant les classes concernées).

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

En production : placer l'application derrière un proxy HTTPS (nginx, Caddy), activer les
cookies sécurisés et isoler le moteur (voir `docs/ARCHITECTURE.md`, § Sécurité).
Sauvegarde : copier le fichier SQLite.

## Tests

```sh
python3 -m unittest discover tests
```

## Documentation

- [`docs/QUESTION_FORMAT.md`](docs/QUESTION_FORMAT.md) — écrire des questions (référence complète)
- [`docs/API.md`](docs/API.md) — l'API REST (contrat entre l'interface et le serveur)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — découpage, portabilité, sécurité, algorithme adaptatif
