#!/usr/bin/env python3
"""Fabrique les fichiers du dossier claude-projet/ à partir des sources du dépôt :

  - REFERENCE-QUESTIONNAPP.md : format des questions + bonnes pratiques + questions d'exemple
  - questionnapp_moteur.py    : le moteur en un seul fichier, pour tester des questions hors de l'app

  python3 scripts/build_claude_project.py          (régénère)
  python3 scripts/build_claude_project.py --check  (vérifie que les fichiers sont à jour)
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "claude-projet")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def build_reference():
    fmt = read("docs", "QUESTION_FORMAT.md")
    fmt = fmt.split("## 5. Protocole du moteur")[0].rstrip()
    fmt = fmt.replace("# Format des questions", "## Format des questions", 1)
    fmt = "\n".join(("#" + l) if l.startswith("## ") and not l.startswith("## Format") else l for l in fmt.splitlines())
    bank = sorted(f for f in os.listdir(os.path.join(ROOT, "banque")) if f.endswith(".json"))
    questions = []
    for name in bank:
        questions += json.loads(read("banque", name))["questions"]
    examples = {"format": "questionnapp/questions", "version": 1, "title": "Exemples", "questions": questions}
    practices = read("claude-projet", "_bonnes-pratiques.md").strip()
    parts = [
        "# Référence QuestionnApp pour la création de questions",
        "",
        "> Fichier généré par `scripts/build_claude_project.py` — ne pas modifier à la main.",
        "",
        fmt,
        "",
        practices,
        "",
        "## Fichier d'import et questions d'exemple",
        "",
        "Le fichier à produire a exactement cette structure (`format`, `version`, `title` et `description` de la banque, puis la liste `questions`). "
        "Chaque question : `title`, `chapter`, `difficulty` (1 facile, 2 moyen, 3 difficile), `skills` (liste), "
        f"`template`. Voici les {len(questions)} questions de la banque fournie avec l'application, toutes testées : "
        "elles montrent les bons usages de chaque type de champ.",
        "",
        "```json",
        json.dumps(examples, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return "\n".join(parts)


BUNDLE_HEAD = '''#!/usr/bin/env python3
"""Moteur QuestionnApp en un seul fichier (généré par scripts/build_claude_project.py).

Sert à tester des questions hors de l'application, par exemple dans l'environnement
d'exécution de Claude :

    python3 questionnapp_moteur.py questions.json            # auto-test de chaque question
    python3 questionnapp_moteur.py questions.json --apercu   # + un exemple d'énoncé par question

Depuis Python :

    import questionnapp_moteur as m
    m.selftest(template)          # rapport : status ok / warning / error
    m.preview(template, seed=1)   # énoncé, réponses attendues, variété

Les garde-fous d'exécution (bac à sable) ne sont pas activés ici : ne l'utilisez que pour
tester vos propres questions.
"""

import importlib.util
import json
import sys
import types

_SOURCES = {SOURCES}


def _load():
    pkg = types.ModuleType("qa_moteur")
    pkg.__path__ = []
    sys.modules["qa_moteur"] = pkg
    for name in ("sandbox", "helpers", "core"):
        full = "qa_moteur." + name
        mod = types.ModuleType(full)
        mod.__package__ = "qa_moteur"
        mod.__file__ = "<" + full + ">"
        sys.modules[full] = mod
        exec(compile(_SOURCES[name], mod.__file__, "exec"), mod.__dict__)
        setattr(pkg, name, mod)
    return sys.modules["qa_moteur.core"]


core = _load()
generate, preview, check, selftest, TemplateError = core.generate, core.preview, core.check, core.selftest, core.TemplateError


def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"] if isinstance(data, dict) and "questions" in data else (data if isinstance(data, list) else [data])
    show = "--apercu" in argv
    worst = 0
    for i, q in enumerate(questions, 1):
        template = q.get("template", q)
        r = selftest(template, samples=20)
        mark = {"ok": "OK   ", "warning": "AVERT", "error": "ERREUR"}[r["status"]]
        worst = max(worst, {"ok": 0, "warning": 1, "error": 2}[r["status"]])
        print(f"[{mark}] {i}. {q.get('title', '(sans titre)')} : {r['samples']} tirage(s), {r['distinct']} énoncé(s) différent(s)")
        for e in r["errors"]:
            where = f" [{e.get('where')}{', ligne ' + str(e['line']) if e.get('line') else ''}]" if e.get("where") else ""
            print(f"        erreur{where} : {e['error']}")
        for w in r["warnings"]:
            print(f"        attention : {w}")
        if show and r["samples"]:
            p = preview(template, 1)
            print("        --- exemple d'énoncé ---")
            for line in p["public"]["statement"].splitlines():
                print("        " + line)
            print("        --- réponses attendues : " + " | ".join(str(x) for x in p["expected"]))
    return worst


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
'''


def build_bundle():
    sources = {name: read("engine", f"{name}.py") for name in ("sandbox", "helpers", "core")}
    body = "{\n" + "".join(f"    {k!r}: {v!r},\n" for k, v in sources.items()) + "}"
    return BUNDLE_HEAD.replace("{SOURCES}", body)


def outputs():
    return {"REFERENCE-QUESTIONNAPP.md": build_reference(), "questionnapp_moteur.py": build_bundle()}


def main():
    check = "--check" in sys.argv
    stale = []
    for name, content in outputs().items():
        path = os.path.join(OUT, name)
        if check:
            try:
                current = open(path, encoding="utf-8").read()
            except FileNotFoundError:
                current = None
            if current != content:
                stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"écrit : claude-projet/{name} ({len(content) // 1024} Ko)")
    if stale:
        print("À régénérer (python3 scripts/build_claude_project.py) : " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
