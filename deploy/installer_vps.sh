#!/usr/bin/env bash
# =============================================================================
#  Installation complète de ReadyMatch sur un VPS Ubuntu 22.04 / 24.04 (Contabo…)
#  Usage (en root ou avec sudo) :
#     bash installer_vps.sh readymatch.mondomaine.cm moi@exemple.cm   # avec domaine : HTTPS automatique
#     bash installer_vps.sh 203.0.113.10                                # sans domaine : HTTP sur l'IP
#  Relançable sans risque : ce qui existe déjà est conservé, le code est mis à jour.
# =============================================================================
set -euo pipefail
HOTE="${1:?Indiquez le domaine (ex. readymatch.mondomaine.cm) ou l’IP du VPS}"
EMAIL="${2:-}"
DEPOT="${DEPOT:-https://github.com/yoantioma/Ankadez.git}"
BRANCHE="${BRANCHE:-main}"
U=readymatch
RACINE=/srv/readymatch
APP=$RACINE/app

[ "$(id -u)" -eq 0 ] || { echo "Lancez ce script en root : sudo bash $0 $*"; exit 1; }
EST_IP=false; [[ "$HOTE" =~ ^[0-9.]+$ ]] && EST_IP=true

echo "▶ 1/8 Paquets système"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3-venv python3-dev build-essential postgresql nginx git ufw certbot python3-certbot-nginx

echo "▶ 2/8 Pare-feu (SSH, HTTP, HTTPS)"
ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null

echo "▶ 3/8 Utilisateur système « $U »"
id "$U" &>/dev/null || adduser --system --group --home "$RACINE" --shell /bin/bash "$U"
usermod -aG www-data "$U"
chmod 755 "$RACINE"

echo "▶ 4/8 Base PostgreSQL"
DBPASS=""
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$U'" | grep -q 1; then
  DBPASS=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
  sudo -u postgres psql -q -c "CREATE USER $U WITH PASSWORD '$DBPASS';"
  sudo -u postgres psql -q -c "CREATE DATABASE $U OWNER $U;"
fi

echo "▶ 5/8 Code depuis $DEPOT"
if [ -d "$APP/.git" ]; then
  sudo -u "$U" git -C "$APP" pull --ff-only
else
  sudo -u "$U" git clone -q -b "$BRANCHE" "$DEPOT" "$APP"
fi
cd "$APP"
[ -d .venv ] || sudo -u "$U" python3 -m venv .venv
sudo -u "$U" .venv/bin/pip install -q --upgrade pip
sudo -u "$U" .venv/bin/pip install -q -r requirements.txt

echo "▶ 6/8 Configuration (.env) et base de données"
if [ ! -f .env ]; then
  [ -n "$DBPASS" ] || { echo "La base existe déjà mais .env est absent : recréez-le à partir de .env.example."; exit 1; }
  SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(64))")
  if $EST_IP; then SSL=False; ORIGINE="http://$HOTE"; else SSL=True; ORIGINE="https://$HOTE"; fi
  cat > .env <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$HOTE
DJANGO_CSRF_TRUSTED_ORIGINS=$ORIGINE
DATABASE_URL=postgres://$U:$DBPASS@127.0.0.1:5432/$U
DJANGO_SECURE_SSL=$SSL
DJANGO_HSTS_SECONDS=0
DJANGO_STATIC_ROOT=staticfiles
DJANGO_MEDIA_ROOT=media
EOF
  chown "$U:$U" .env
  chmod 600 .env
fi
sudo -u "$U" mkdir -p media
sudo -u "$U" .venv/bin/python manage.py migrate --noinput
sudo -u "$U" .venv/bin/python manage.py collectstatic --noinput -v 0

echo "▶ 7/8 Service Gunicorn et Nginx"
cp deploy/readymatch.service /etc/systemd/system/readymatch.service
systemctl daemon-reload
systemctl enable readymatch >/dev/null
systemctl restart readymatch
sed "s/readymatch.exemple.cm/$HOTE/" deploy/nginx_readymatch.conf > /etc/nginx/sites-available/readymatch
ln -sf /etc/nginx/sites-available/readymatch /etc/nginx/sites-enabled/readymatch
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "▶ 8/8 HTTPS"
if $EST_IP; then
  echo "  Adresse IP : pas de certificat possible, le site est servi en HTTP."
elif [ -n "$EMAIL" ]; then
  certbot --nginx -d "$HOTE" --non-interactive --agree-tos -m "$EMAIL" --redirect
else
  certbot --nginx -d "$HOTE"
fi

echo
echo "✔ ReadyMatch est en ligne : $( $EST_IP && echo "http" || echo "https" )://$HOTE"
echo "  Étapes suivantes (facultatives) :"
echo "   - compte administrateur :  sudo -u $U $APP/.venv/bin/python $APP/manage.py createsuperuser"
echo "   - annuaire depuis les CSV : sudo -u $U $APP/.venv/bin/python $APP/manage.py import_panaf '$RACINE/ajouts_panaf_*.csv'"
echo "   - données de démonstration (aperçus de la vitrine) : sudo -u $U $APP/.venv/bin/python $APP/manage.py seed_demo"
echo "   - mises à jour après un git push : sudo bash $APP/deploy/deploy.sh"
