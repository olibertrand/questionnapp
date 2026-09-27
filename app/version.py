"""Version de l'application : commit git courant (lu directement dans .git, sans lancer git)."""

import datetime
import os

from . import config


def _git_commit():
    git = os.path.join(config.ROOT, ".git")
    try:
        with open(os.path.join(git, "HEAD"), encoding="utf-8") as f:
            head = f.read().strip()
        if not head.startswith("ref: "):
            return head, None
        ref = head[5:]
        branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
        path = os.path.join(git, ref)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read().strip(), branch
        with open(os.path.join(git, "packed-refs"), encoding="utf-8") as f:
            for line in f:
                if line.strip().endswith(" " + ref):
                    return line.split()[0], branch
    except OSError:
        pass
    return None, None


def info():
    commit, branch = _git_commit()
    stamp = None
    if commit:
        try:
            obj = os.path.join(config.ROOT, ".git", "objects", commit[:2], commit[2:])
            if os.path.exists(obj):
                stamp = datetime.datetime.fromtimestamp(os.path.getmtime(obj)).strftime("%d/%m/%Y %H:%M")
        except OSError:
            pass
    return {"commit": commit[:7] if commit else None, "branch": branch, "date": stamp}
