# Créer des questions avec Claude à partir de son cours

Ce dossier contient tout ce qu'il faut pour un **projet Claude** (claude.ai) qui transforme un
cours et ses exercices en questions pour QuestionnApp, y compris sur les **prérequis** que les
exercices mobilisent (des dictionnaires dans un chapitre de POO, par exemple).

| Fichier | Rôle |
|---|---|
| `INSTRUCTIONS.md` | texte à coller dans les instructions du projet |
| `REFERENCE-QUESTIONNAPP.md` | à ajouter aux connaissances du projet : format complet, bonnes pratiques, 25 questions d'exemple |
| `questionnapp_moteur.py` | à ajouter aussi : le moteur de l'application en un seul fichier, pour que Claude teste ses questions |

## Mise en place (une seule fois)

1. Sur claude.ai, **Projets → Créer un projet**, par exemple « Questions NSI ».
2. **Instructions du projet** : coller le contenu de `INSTRUCTIONS.md`.
3. **Connaissances du projet** : ajouter `REFERENCE-QUESTIONNAPP.md` et `questionnapp_moteur.py`.
4. Dans les paramètres de Claude, activer l'**exécution de code et la création de fichiers**
   (c'est ce qui permet à Claude de tester les questions avant de vous les donner et de vous
   fournir un fichier à télécharger).

## Pour chaque chapitre

1. Dans QuestionnApp, page **Questions**, cliquer sur **Référentiel pour Claude** : cela
   télécharge `referentiel-questionnapp.md` (vos chapitres, compétences et questions existantes).
2. Dans le projet Claude, ouvrir une **nouvelle conversation** et y déposer :
   le référentiel, le cours, les exercices (PDF, texte, notebooks…). Par exemple :
   > Voici mon cours et mes exercices sur la POO (chapitre 2). Propose-moi un plan de questions.
3. Claude propose un plan : notions du chapitre, prérequis repérés dans les exercices, et la
   liste des questions envisagées. Ajustez (« ajoute des questions sur les dictionnaires »,
   « pas de SQL », « plus de questions de code »), puis validez.
4. Claude écrit les questions, les teste avec `questionnapp_moteur.py` s'il le peut, et vous
   donne un fichier `questions-….json`.
   Si Claude indique ne pas trouver le moteur, joignez `questionnapp_moteur.py` directement à la
   conversation.
5. Dans QuestionnApp : **Questions → Importer (JSON)**. Chaque question est testée à nouveau
   (20 tirages) : celles qui ne fonctionnent pas sont refusées, celles qui sont douteuses sont
   importées mais signalées « à vérifier ».
6. Relisez chaque nouvelle question avec **Aperçu** (plusieurs tirages avec 🎲), corrigez-la si
   besoin dans l'éditeur (bouton **Vérifier** pour relancer l'auto-test), puis affectez-la à vos
   classes.

## Conseils

- Une conversation par chapitre garde un contexte clair ; le projet conserve la référence.
- Plus vos exercices sont fournis, mieux Claude repère les prérequis réellement utilisés.
- Si un type de question vous plaît particulièrement, dites-le : « fais d'autres questions comme
  celle-ci ». Vous pouvez aussi exporter une question réussie (**Exporter (JSON)**) et la donner
  en exemple.
- Relisez toujours : Claude peut se tromper sur le niveau attendu ou sur une subtilité du cours.

## Maintenance

`REFERENCE-QUESTIONNAPP.md` et `questionnapp_moteur.py` sont générés à partir du code de
l'application (`python3 scripts/build_claude_project.py`). Après une mise à jour de
QuestionnApp, remplacez-les dans les connaissances du projet.
