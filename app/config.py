"""Configuration par variables d'environnement."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HOST = os.environ.get("QUESTIONNAPP_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUESTIONNAPP_PORT", "8000"))
DB_PATH = os.environ.get("QUESTIONNAPP_DB", os.path.join(ROOT, "data", "questionnapp.db"))
WEB_DIR = os.path.join(ROOT, "web")
# Répertoire des banques de questions (un fichier JSON par thème), voir banque/LISEZMOI.md
BANK_DIR = os.environ.get("QUESTIONNAPP_BANK_DIR", os.path.join(ROOT, "banque"))
SESSION_DAYS = int(os.environ.get("QUESTIONNAPP_SESSION_DAYS", "7"))
# Mettre à 1 derrière un proxy HTTPS pour poser des cookies « Secure »
SECURE_COOKIES = os.environ.get("QUESTIONNAPP_SECURE_COOKIES", "0") == "1"
# Préfixe de commande pour isoler le moteur, ex. "firejail --quiet --net=none"
SANDBOX_CMD = os.environ.get("QUESTIONNAPP_SANDBOX_CMD", "")
ENGINE_TIMEOUT = float(os.environ.get("QUESTIONNAPP_ENGINE_TIMEOUT", "25"))
