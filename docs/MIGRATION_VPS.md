# Migration de QuestionnApp de l'Odroid vers un VPS

Objectif : faire tourner QuestionnApp sur un VPS (serveur loué, dans un datacenter de l'Union
européenne), sans perdre aucune donnée des élèves, en gardant l'Odroid comme solution de
retour pendant une semaine, puis comme machine de sauvegarde (et pour `chat`).

Décisions prises :
- VPS Hostinger, formule **KVM 2** (8 Go de mémoire, pour accueillir plus tard une forge Git),
  datacenter dans l'UE, **Ubuntu LTS**.
- On garde **SQLite** (un seul fichier) sur le VPS, avec sauvegarde chaque nuit **copiée sur
  l'Odroid**.
- **Caddy** pour le HTTPS : il sert déjà une autre appli (`audio`) sur le VPS et obtient tout
  seul les certificats (Let's Encrypt). La configuration de QuestionnApp est dans un fichier à part
  (`deploy/questionnapp.caddy`), inclus par le Caddyfile principal : l'autre appli n'est pas touchée.
- Seul le sous-domaine de QuestionnApp change d'adresse ; le domaine principal et `chat`
  restent chez ChangeIP, pointés vers la maison.

Dans ce document : `DOMAINE` = le sous-domaine de l'appli, `IP_DU_VPS` = l'adresse du VPS
(donnée par Hostinger), `UTILISATEUR` = ton nom d'utilisateur sur le VPS. Aucune de ces valeurs
ne doit être écrite dans le dépôt.

Légende : ⏸ = étape où l'on s'arrête pour vérifier avant de continuer.

---

## Phase 0 — Avant de commencer (rien ne change pour les élèves)

1. **Vérifier le DNS dynamique** (box, Odroid, espace ChangeIP) : savoir si un programme met à
   jour les adresses de `jeangi.org`, et lesquelles. S'il met à jour le sous-domaine de l'appli
   ou tout le domaine (`*`), il faudra l'en exclure, sinon il réécrirait l'adresse du VPS.
2. **Mettre l'Odroid à jour** (`git pull`, redémarrage de l'appli) pour qu'il ait les scripts de
   sauvegarde, puis faire une première sauvegarde et la tester :
   ```sh
   python3 scripts/sauvegarde.py
   python3 scripts/restaurer.py --test <fichier affiché>
   ```
3. **Commander le VPS** : KVM 2, Ubuntu LTS (24.04 ou plus récent), datacenter UE. Dans le
   formulaire, choisir l'authentification **par clé SSH** si c'est proposé (étape 4).
4. **Créer une clé SSH dédiée au VPS**, sur ton ordinateur (jamais une clé qui sert ailleurs) :
   ```sh
   ssh-keygen -t ed25519 -f ~/.ssh/vps_questionnapp -C "vps questionnapp"
   ```
   La clé **publique** (`~/.ssh/vps_questionnapp.pub`) se colle dans le panneau Hostinger ; la
   clé **privée** ne quitte jamais ton ordinateur.
5. **Baisser le TTL** de l'enregistrement de l'appli chez ChangeIP à 300 secondes (5 minutes),
   au moins un jour avant la bascule.

⏸ Vérifier : `ssh -i ~/.ssh/vps_questionnapp root@IP_DU_VPS` ouvre une session sur le VPS.

## Phase 1 — Compte d'administration et durcissement du VPS

Toutes les commandes de cette phase se tapent sur le VPS.

1. Mettre le système à jour et créer ton utilisateur (avec les droits d'administration par
   `sudo`) :
   ```sh
   apt update && apt -y upgrade
   adduser UTILISATEUR
   usermod -aG sudo UTILISATEUR
   mkdir -p /home/UTILISATEUR/.ssh
   cp /root/.ssh/authorized_keys /home/UTILISATEUR/.ssh/
   chown -R UTILISATEUR:UTILISATEUR /home/UTILISATEUR/.ssh && chmod 700 /home/UTILISATEUR/.ssh
   ```
   ⏸ Depuis ton ordinateur, dans un **second** terminal (garder le premier ouvert) :
   `ssh -i ~/.ssh/vps_questionnapp UTILISATEUR@IP_DU_VPS` puis `sudo whoami` doit répondre `root`.
2. **Interdire** la connexion directe en administrateur et la connexion par mot de passe :
   ```sh
   sudo tee /etc/ssh/sshd_config.d/99-durcissement.conf <<'EOF'
   PermitRootLogin no
   PasswordAuthentication no
   KbdInteractiveAuthentication no
   EOF
   sudo systemctl reload ssh
   ```
   ⏸ Dans un nouveau terminal : `ssh root@IP_DU_VPS` doit être **refusé**, et
   `ssh -i ~/.ssh/vps_questionnapp UTILISATEUR@IP_DU_VPS` doit toujours marcher.
3. **Pare-feu** : n'ouvrir que SSH (administration), 80 et 443 (web) :
   ```sh
   sudo ufw allow OpenSSH
   sudo ufw allow 80/tcp
   sudo ufw allow 443          # TCP et UDP (Caddy utilise aussi HTTP/3)
   sudo ufw enable
   sudo ufw status verbose
   ```
   Si le panneau Hostinger propose aussi un pare-feu, y mettre les mêmes règles.
4. **Mises à jour de sécurité automatiques** :
   ```sh
   sudo apt -y install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades   # répondre « Oui »
   ```

⏸ Vérifier : `sudo ufw status` n'affiche que 22 (OpenSSH), 80 et 443 ;
`cat /etc/apt/apt.conf.d/20auto-upgrades` contient deux lignes à `"1"`.

## Phase 2 — Installation de l'appli (invisible pour les élèves)

1. Paquets nécessaires (Python est déjà fourni par Ubuntu, en version 3.11 ou plus) :
   ```sh
   sudo apt -y install git rsync
   python3 --version
   ```
2. Utilisateur système dédié à l'appli, dossier du code et dossier des données :
   ```sh
   sudo adduser --system --group --home /var/lib/questionnapp questionnapp
   sudo mkdir -p /opt/questionnapp /var/lib/questionnapp/sauvegardes
   sudo chown questionnapp:questionnapp /opt/questionnapp /var/lib/questionnapp /var/lib/questionnapp/sauvegardes
   sudo -u questionnapp git clone https://github.com/olibertrand/questionnapp.git /opt/questionnapp
   ```
   (Si le dépôt est privé, il faudra une « clé de déploiement » en lecture seule, ajoutée dans
   les réglages du dépôt sur GitHub ; je te guiderai à ce moment-là.)
3. Service (démarrage automatique) :
   ```sh
   sudo cp /opt/questionnapp/deploy/questionnapp.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now questionnapp
   sudo journalctl -u questionnapp --no-pager | tail
   ```
   Au tout premier démarrage, sur une base vide, le journal affiche un mot de passe `admin`
   provisoire : il ne servira pas, la vraie base sera copiée en phase 4.
4. Préparer le site Caddy, **sans l'activer** : tant que le sous-domaine pointe vers l'Odroid,
   Caddy ne pourrait pas obtenir le certificat (il réessaierait en boucle). On l'active à la
   bascule (phase 5).
   ```sh
   sudo cp /opt/questionnapp/deploy/questionnapp.caddy /etc/caddy/questionnapp.caddy
   sudo sed -i 's/^DOMAINE {/le.sous-domaine.de.l.appli {/' /etc/caddy/questionnapp.caddy
   ```
   Attention : le Caddyfile principal (`/etc/caddy/Caddyfile`) est réécrit par le script
   d'installation de l'autre appli (`audio`). Si on relance ce script, il faudra remettre la
   ligne `import /etc/caddy/questionnapp.caddy` (phase 5) — ou, mieux, l'ajouter à ce script.
5. Sauvegarde chaque nuit sur le VPS (`sudo crontab -u questionnapp -e`) :
   ```
   17 2 * * * cd /opt/questionnapp && QUESTIONNAPP_DB=/var/lib/questionnapp/questionnapp.db QUESTIONNAPP_BACKUP_DIR=/var/lib/questionnapp/sauvegardes python3 scripts/sauvegarde.py >> /var/lib/questionnapp/sauvegardes.log 2>&1
   ```

⏸ Vérifier : `curl -s http://127.0.0.1:8000/api/version` répond (sur le VPS), et depuis ton
ordinateur `https://audio.jeangi.org` marche toujours (l'autre appli n'est pas touchée). L'appli
n'est pas encore joignable depuis Internet : c'est voulu, on la teste en phase 4 par un tunnel.

## Phase 3 — Sauvegardes hors du VPS (vers l'Odroid)

1. Sur l'**Odroid**, une clé SSH qui ne servira qu'à ça :
   ```sh
   ssh-keygen -t ed25519 -f ~/.ssh/questionnapp_sauvegardes -N "" -C "odroid sauvegardes"
   cat ~/.ssh/questionnapp_sauvegardes.pub
   ```
2. Sur le **VPS**, un compte `sauvegarde` qui ne peut que **lire** le dossier des sauvegardes
   (grâce à `rrsync`, fourni avec rsync) :
   ```sh
   sudo adduser --disabled-password --gecos "" sauvegarde
   sudo usermod -aG questionnapp sauvegarde
   sudo chmod 750 /var/lib/questionnapp /var/lib/questionnapp/sauvegardes
   sudo mkdir -p /home/sauvegarde/.ssh
   echo 'command="rrsync -ro /var/lib/questionnapp/sauvegardes",restrict COLLER_ICI_LA_CLE_PUBLIQUE' | sudo tee /home/sauvegarde/.ssh/authorized_keys
   sudo chown -R sauvegarde:sauvegarde /home/sauvegarde/.ssh && sudo chmod 600 /home/sauvegarde/.ssh/authorized_keys
   ```
3. Sur l'**Odroid**, chaque matin (`crontab -e`), avec le script fourni :
   ```
   30 6 * * * VPS=sauvegarde@IP_DU_VPS sh /chemin/vers/questionnapp/deploy/recuperer_sauvegardes.sh >> ~/sauvegardes-questionnapp.log 2>&1
   ```

⏸ Vérifier : lancer la commande une fois à la main sur l'Odroid ; les fichiers
`questionnapp-….db` apparaissent dans `~/sauvegardes-questionnapp/`.

## Phase 4 — Répétition générale (les élèves restent sur l'Odroid)

1. Sur l'Odroid : `python3 scripts/sauvegarde.py --dossier ~/migration`.
2. Copier ce fichier vers le VPS, par exemple
   `scp -i ~/.ssh/vps_questionnapp fichier.db UTILISATEUR@IP_DU_VPS:/tmp/`, puis sur le VPS :
   ```sh
   sudo install -o questionnapp -g questionnapp -m 600 /tmp/fichier.db /var/lib/questionnapp/import.db
   sudo systemctl stop questionnapp
   sudo -u questionnapp env QUESTIONNAPP_DB=/var/lib/questionnapp/questionnapp.db python3 /opt/questionnapp/scripts/restaurer.py /var/lib/questionnapp/import.db --oui
   sudo systemctl start questionnapp
   sudo rm /tmp/fichier.db /var/lib/questionnapp/import.db
   ```
3. Tester à travers un **tunnel SSH** (le trafic passe chiffré dans la connexion SSH, et les
   cookies sécurisés de l'appli fonctionnent sur `localhost`) : depuis ton ordinateur,
   ```sh
   ssh -i ~/.ssh/vps_questionnapp -L 8000:127.0.0.1:8000 UTILISATEUR@IP_DU_VPS
   ```
   puis ouvrir `http://localhost:8000` dans le navigateur, tant que cette session reste ouverte :
   connexion prof, classes, statistiques, aperçu d'une question de code. Les chiffres doivent
   être ceux de l'Odroid.

⏸ Vérifier : le nombre de comptes, de questions et de réponses affiché par `restaurer.py` est
le même que sur l'Odroid.

## Phase 5 — Bascule (hors cours, environ 30 minutes)

1. Sur l'Odroid : **arrêter l'appli** (plus personne ne peut répondre pendant la bascule).
2. Dernière sauvegarde sur l'Odroid, copie vers le VPS, restauration (comme en phase 4).
3. Chez ChangeIP : remplacer l'enregistrement de l'appli (alias `CNAME` vers `jeangi.org`) par
   un enregistrement **`A` vers `IP_DU_VPS`**. Ne toucher ni à `jeangi.org`, ni à `chat`.
4. Attendre que le nom pointe vers le VPS (`ping DOMAINE` affiche `IP_DU_VPS`), puis sur le VPS,
   activer le site (Caddy demande alors le certificat HTTPS tout seul, en quelques secondes) :
   ```sh
   grep -q 'import /etc/caddy/questionnapp.caddy' /etc/caddy/Caddyfile \
     || echo 'import /etc/caddy/questionnapp.caddy' | sudo tee -a /etc/caddy/Caddyfile
   sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   sudo systemctl reload caddy
   sudo journalctl -u caddy --no-pager --since "5 min ago" | grep -i -E 'certificate|error'
   ```
   `caddy validate` doit répondre « Valid configuration » **avant** le `reload` ; sinon, ne pas
   recharger et me montrer le message (l'autre appli continue de tourner avec l'ancienne
   configuration).
5. Vérifier depuis ton **téléphone en 4G** : `https://DOMAINE` s'ouvre avec le cadenas, connexion
   prof, connexion élève, réponse à une question, la version en bas de page.

**Plan de retour** (en cas de problème pendant ou après la bascule) : remettre chez ChangeIP
l'alias `CNAME` vers `jeangi.org` et redémarrer l'appli sur l'Odroid. Attention : les réponses
données sur le VPS entre-temps ne seront pas sur l'Odroid (on peut les récupérer en copiant la
base du VPS vers l'Odroid avec les mêmes scripts).

## Phase 6 — Après la bascule

1. Pendant une semaine : l'Odroid garde l'ancienne base et sa configuration, sans servir l'appli.
2. Ensuite : retirer la partie de l'appli de la configuration nginx **de l'Odroid** (garder `chat`),
   remettre le TTL à sa valeur habituelle.
3. Mettre à jour `AGENTS.md` (« Où on en est » : l'appli tourne sur le VPS) et les
   instructions de mise à jour : désormais, après chaque fusion sur GitHub,
   `sudo sh /opt/questionnapp/deploy/mettre_a_jour.sh` sur le VPS (sauvegarde, `git pull`,
   redémarrage).
4. Lancer le prompt de vérification de la stack (preuves à l'appui).

## Pour plus tard
- `chat` passe par le VPS à travers un tunnel chiffré ouvert par l'Odroid : plus aucun port
  ouvert à la maison.
- Isolement renforcé du code des élèves (`QUESTIONNAPP_SANDBOX_CMD`, par exemple avec
  `firejail`) — garde-fou : à valider avant.
- Forge Git (GitLab, ou Forgejo, beaucoup plus léger) sur le même VPS, derrière Caddy.
