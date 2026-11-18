#!/bin/sh
# Démarrage du conteneur : attendre PostgreSQL, appliquer les migrations, rassembler les fichiers statiques, puis lancer Gunicorn.
set -e

echo "▶ Attente de la base de données…"
python - <<'PY'
import os, time, sys
import dj_database_url, psycopg
url = os.environ.get("DATABASE_URL", "")
if not url.startswith("postgres"):
    sys.exit(0)
cfg = dj_database_url.parse(url)
for i in range(60):
    try:
        psycopg.connect(host=cfg["HOST"], port=cfg["PORT"] or 5432, user=cfg["USER"], password=cfg["PASSWORD"], dbname=cfg["NAME"], connect_timeout=3).close()
        print("  base prête")
        break
    except Exception:
        time.sleep(2)
else:
    sys.exit("La base de données ne répond pas.")
PY

echo "▶ Migrations"
python manage.py migrate --noinput

echo "▶ Fichiers statiques"
python manage.py collectstatic --noinput -v 0

echo "▶ Démarrage : $*"
exec "$@"
