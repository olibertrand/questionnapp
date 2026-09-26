"""Point d'entrée du moteur : une requête JSON sur stdin, une réponse JSON sur stdout.

Requêtes :
  {"action": "generate", "template": {...}, "seed": 123, "avoid": ["empreinte", ...]}
  {"action": "preview",  "template": {...}, "seed": 123}
  {"action": "check",    "template": {...}, "seed": 123, "answers": [...]}
Réponse : {"ok": true, "result": {...}} ou {"ok": false, "error": "...", "where": ..., "line": ...}

Lancement : python3 -I -m engine.runner   (depuis la racine du projet)
"""

import io
import json
import os
import sys


def main():
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()  # protège le canal de réponse des print() parasites
    try:
        request = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        real_stdout.write(json.dumps({"ok": False, "error": f"requête JSON invalide : {exc}"}))
        return

    from . import core, sandbox

    action = request.get("action")
    if os.environ.get("QUESTIONNAPP_NO_SANDBOX") != "1":
        cpu = int(os.environ.get("QUESTIONNAPP_CPU_LIMIT", "20"))
        sandbox.install(cpu_seconds=cpu * 3 if action == "selftest" else cpu)

    template = request.get("template") or {}
    seed = int(request.get("seed") or 0) & 0xFFFFFFFF
    try:
        if action == "generate":
            result = core.generate(template, seed, request.get("avoid") or (), int(request.get("max_tries") or 25))
        elif action == "preview":
            result = core.preview(template, seed)
        elif action == "selftest":
            result = core.selftest(template, int(request.get("samples") or 20))
        elif action == "check":
            result = core.check(template, seed, request.get("answers") or [])
        else:
            raise core.TemplateError(f"action inconnue : {action!r}")
        response = {"ok": True, "result": result}
    except core.TemplateError as exc:
        response = {"ok": False, **exc.to_dict()}
    except core.TimeLimit as exc:
        response = {"ok": False, "error": f"Le générateur est trop lent : {exc}", "where": "code"}
    except sandbox.SandboxViolation as exc:
        response = {"ok": False, "error": f"Opération interdite : {exc}", "where": "code"}
    except MemoryError:
        response = {"ok": False, "error": "Mémoire insuffisante", "where": "code"}
    except Exception as exc:  # noqa: BLE001
        response = {"ok": False, "error": f"Erreur interne du moteur : {type(exc).__name__}: {exc}"}
    real_stdout.write(json.dumps(response, ensure_ascii=False, default=str))
    real_stdout.flush()


if __name__ == "__main__":
    main()
