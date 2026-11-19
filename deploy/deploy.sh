#!/usr/bin/env bash
# Mise à jour de AnkadeZ sur le VPS, après un « git push » depuis votre poste.
# À lancer en root (ou avec sudo) :  sudo bash /srv/ankadez/app/deploy/deploy.sh
set -euo pipefail
APP=/srv/ankadez/app
U=ankadez
cd "$APP"

sudo -u "$U" git pull --ff-only
sudo -u "$U" .venv/bin/pip install -q -r requirements.txt
sudo -u "$U" .venv/bin/python manage.py migrate --noinput
sudo -u "$U" .venv/bin/python manage.py collectstatic --noinput
systemctl restart ankadez
systemctl --no-pager --lines=3 status ankadez
echo "AnkadeZ est à jour."
