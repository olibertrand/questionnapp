"""Appel du moteur de questions dans un sous-processus isolé (protocole JSON)."""

import json
import os
import shlex
import subprocess
import sys
import tempfile

from . import config
from .web import HttpError

_BOOT = f"import sys; sys.path.insert(0, {config.ROOT!r}); from engine.runner import main; main()"


def call(request, timeout=None):
    cmd = shlex.split(config.SANDBOX_CMD) + [sys.executable, "-I", "-c", _BOOT]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
    for key in ("QUESTIONNAPP_NO_SANDBOX", "QUESTIONNAPP_CPU_LIMIT"):
        if key in os.environ:
            env[key] = os.environ[key]
    with tempfile.TemporaryDirectory(prefix="qa-engine-") as cwd:
        try:
            proc = subprocess.run(cmd, input=json.dumps(request, ensure_ascii=False), capture_output=True,
                                  text=True, timeout=timeout or config.ENGINE_TIMEOUT, cwd=cwd, env=env,
                                  encoding="utf-8")
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Délai dépassé : le code ne s'arrête pas ou est trop lent."}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        detail = (proc.stderr or "").strip().splitlines()[-1:] or ["processus interrompu"]
        if proc.returncode and proc.returncode < 0:
            detail = ["limite de temps ou de mémoire atteinte"]
        return {"ok": False, "error": f"Le moteur a échoué : {detail[0]}"}


def call_or_raise(request, status=422):
    res = call(request)
    if not res.get("ok"):
        raise HttpError(status, res.get("error", "Erreur du moteur"), where=res.get("where"), line=res.get("line"))
    return res["result"]
