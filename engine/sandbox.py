"""Garde-fous d'exécution pour le code des modèles (profs) et des élèves.

Ce n'est PAS un bac à sable parfait : en production exposée à Internet, faire
tourner le moteur dans un conteneur sans réseau (voir QUESTIONNAPP_SANDBOX_CMD
dans docs/ARCHITECTURE.md). Ici on combine :
  * limites système (CPU, mémoire, taille de fichiers, nombre de processus) ;
  * un « audit hook » Python qui bloque réseau, processus, écriture de fichiers,
    lecture de fichiers hors de la bibliothèque standard, ctypes, etc. ;
  * un délai maximal côté appelant (le serveur tue le processus).
"""

import os
import sys
import sysconfig

try:
    import resource
except ImportError:  # Windows : pas de limites système
    resource = None

# Modules que le code des modèles et des élèves peut importer.
ALLOWED_IMPORTS = {
    "math", "random", "itertools", "functools", "collections", "string", "re",
    "heapq", "bisect", "statistics", "fractions", "decimal", "copy", "typing",
    "dataclasses", "textwrap", "operator", "sqlite3", "json", "time", "datetime",
    "array", "enum", "abc", "numbers", "cmath", "pprint", "unicodedata",
}

_BLOCKED_PREFIXES = (
    "socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn",
    "os.fork", "os.forkpty", "os.kill", "os.killpg", "os.remove", "os.unlink",
    "os.rmdir", "os.rename", "os.mkdir", "os.chmod", "os.chown", "os.truncate",
    "os.symlink", "os.link", "os.putenv", "os.unsetenv", "os.chdir", "os.listdir",
    "os.scandir", "os.walk", "shutil.", "ctypes.", "urllib.", "http.", "ftplib.",
    "smtplib.", "webbrowser.", "pty.", "winreg.", "msvcrt.", "code.__new__",
    "marshal.", "pickle.", "shelve.", "glob.", "setopencodehook",
    "sys.addaudithook", "sys.setprofile", "sys.settrace", "gc.get_referrers",
    "gc.get_objects",
)

_STDLIB_DIRS = tuple(
    os.path.realpath(p) for p in {
        sysconfig.get_paths().get("stdlib"),
        sysconfig.get_paths().get("platstdlib"),
    } if p
)
_ENGINE_DIR = os.path.realpath(os.path.dirname(__file__))


class SandboxViolation(Exception):
    pass


# Vrai pendant l'exécution du code d'un élève (et des tests qui l'appellent) : on y interdit
# en plus l'introspection des frames, qui permettrait de lire la réponse attendue.
STUDENT = False

_STUDENT_BLOCKED = ("sys._getframe", "sys._current_frames", "sys._getframemodulename", "object.__getattr__",
                    "gc.", "sys.set", "builtins.input", "cpython.")


def _audit(event, args):
    if STUDENT and event.startswith(_STUDENT_BLOCKED):
        raise SandboxViolation(f"opération interdite ({event})")
    if event == "open":
        path, mode = args[0], args[1]
        if isinstance(path, int):  # descripteur déjà ouvert
            return
        if mode is not None and any(c in str(mode) for c in "wax+"):
            raise SandboxViolation("écriture de fichier interdite")
        real = os.path.realpath(os.fsdecode(path))
        if not (real.startswith(_STDLIB_DIRS) or real.startswith(_ENGINE_DIR)):
            raise SandboxViolation("accès aux fichiers interdit")
        return
    if event == "import":
        name = args[0] or ""
        root = name.split(".")[0]
        if root not in ALLOWED_IMPORTS and name not in sys.modules and not root.startswith("_"):
            raise SandboxViolation(f"import du module « {name} » interdit")
        return
    if event == "sqlite3.connect":
        target = str(args[0]) if args else ""
        if target not in (":memory:", ""):
            raise SandboxViolation("seules les bases SQLite en mémoire sont autorisées")
        return
    for prefix in _BLOCKED_PREFIXES:
        if event.startswith(prefix):
            raise SandboxViolation(f"opération interdite ({event})")


def install(cpu_seconds=10, memory_mb=512):
    """À appeler une seule fois, après les imports nécessaires au moteur."""
    import importlib
    for name in sorted(ALLOWED_IMPORTS):  # pré-charge les dépendances transitives
        try:
            importlib.import_module(name)
        except ImportError:
            pass
    if resource is not None:
        def setlim(which, value):
            try:
                soft, hard = resource.getrlimit(which)
                if hard != resource.RLIM_INFINITY:
                    value = min(value, hard)
                resource.setrlimit(which, (value, value if hard == resource.RLIM_INFINITY else hard))
            except (ValueError, OSError):
                pass
        setlim(resource.RLIMIT_CPU, cpu_seconds)
        setlim(resource.RLIMIT_AS, memory_mb * 1024 * 1024)
        setlim(resource.RLIMIT_FSIZE, 0)
        if hasattr(resource, "RLIMIT_NPROC"):
            setlim(resource.RLIMIT_NPROC, 0)
    sys.setrecursionlimit(3000)
    sys.addaudithook(_audit)
