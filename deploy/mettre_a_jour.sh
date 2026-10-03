#!/bin/sh
# Mise à jour de QuestionnApp sur le VPS après la fusion d'une demande sur GitHub :
#   sudo sh /opt/questionnapp/deploy/mettre_a_jour.sh
# Sauvegarde d'abord la base, récupère la dernière version de main, puis redémarre l'appli.
set -e
cd /opt/questionnapp
sudo -u questionnapp env QUESTIONNAPP_DB=/var/lib/questionnapp/questionnapp.db \
    QUESTIONNAPP_BACKUP_DIR=/var/lib/questionnapp/sauvegardes python3 scripts/sauvegarde.py
sudo -u questionnapp git pull --ff-only
systemctl restart questionnapp
sleep 2
systemctl --no-pager --lines=5 status questionnapp
echo "Version en ligne : $(curl -s http://127.0.0.1:8000/api/version)"
