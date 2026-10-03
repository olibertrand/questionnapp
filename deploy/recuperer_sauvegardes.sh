#!/bin/sh
# À lancer sur l'ODROID (cron, chaque matin) : copie chez soi les sauvegardes faites sur le VPS.
# C'est l'Odroid qui se connecte au VPS : aucun port n'a besoin d'être ouvert à la maison.
# La clé SSH utilisée ne sert qu'à ça, et le VPS ne l'autorise qu'à LIRE le dossier des
# sauvegardes (voir docs/MIGRATION_VPS.md, étape « Sauvegardes hors du VPS »).
#
#   VPS=sauvegarde@ADRESSE_DU_VPS sh recuperer_sauvegardes.sh
set -e
: "${VPS:?indiquer VPS=utilisateur@adresse}"
DEST="${DEST:-$HOME/sauvegardes-questionnapp}"
KEY="${KEY:-$HOME/.ssh/questionnapp_sauvegardes}"
mkdir -p "$DEST"
rsync -a -e "ssh -i $KEY -o BatchMode=yes" "$VPS:" "$DEST/"
# on garde 60 jours de copies à la maison
find "$DEST" -name 'questionnapp-*.db' -mtime +60 -delete
echo "$(date '+%F %T') sauvegardes récupérées dans $DEST ($(ls "$DEST" | wc -l) fichiers)"
