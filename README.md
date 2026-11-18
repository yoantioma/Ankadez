# ReadyMatch · application web (Django)

Landing publique (le Cameroun en chiffres, sans inscription, puis la présentation de l’outil), inscription et onboarding
par profil, espace PME (score, data room, finances, montant légitime, investisseurs) et espace investisseur
(entreprises compatibles, tableau de bord d’une PME, pipeline, thèse). Écrans de chargement à chaque changement
d’écran et à chaque requête.

## Architecture

```
config/            réglages (lus dans .env), urls, wsgi
apps/accounts      utilisateur (connexion par e-mail, rôle), inscription, onboarding, connexion
apps/annuaire      Secteur, Organisation (tous les acteurs : PME, startup, investisseur, institution…), import CSV
apps/pme           profil PME, exercices financiers, pièces de data room, score, montant légitime
apps/investissement thèse d’investissement, indice de compatibilité, demandes d’accès (pipeline)
apps/core          landing, calculs de l’accueil, filtres d’affichage, données de démonstration
templates/ static/ gabarits, styles « Lumière », écrans de chargement (static/js/app.js)
deploy/            Gunicorn, systemd, Nginx, script de mise à jour
```

**Base de données.** Une table `Organisation` pour tous les acteurs ; les données propres à un type vivent dans des
tables liées (`EntrepriseProfile`, `These`). Les montants sont en FCFA (entiers). Les calculs (score, montant,
compatibilité) sont dans des fichiers `services.py`, séparés des vues : ils peuvent passer en tâche de fond ou en API
sans réécriture. SQLite en local, PostgreSQL sur le VPS : seul `DATABASE_URL` change.

## Lancer en local (Windows)

```powershell
cd readymatch_web
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py import_panaf "..\ajouts_panaf_*.csv"
.venv\Scripts\python manage.py seed_demo --comptes --mot-de-passe "VotreMotDePasse"
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

Puis ouvrir http://127.0.0.1:8000. Comptes de test : `pme@demo.cm` et `investisseur@demo.cm`, avec le mot de passe
passé à `seed_demo` (en local, il est noté dans `.env`, variable `DEMO_PASSWORD`).

### Import des CSV

`import_panaf` lit les fichiers `ajouts_panaf_*.csv` (séparateur `;`). Il est idempotent (même ID = mise à jour).
- Entreprise → PME, Startup → startup, Investisseur, Institution, Incubateur, Association, Consultant : importés.
- Talent (des personnes) : non importé. Noms des dirigeants et messages de prospection : jamais importés.
- E-mails et téléphones des organisations : seulement avec `--avec-contacts`.

Les profils importés n’ont pas de comptes financiers : ils comptent dans l’effectif, pas dans « l’argent à se faire ».
Seules les 6 PME de démonstration (`seed_demo`) portent des chiffres, marqués « démonstration ».

## Déployer sur un VPS (Ubuntu 22.04 ou 24.04)

1. **Paquets et utilisateur**
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-dev postgresql nginx certbot python3-certbot-nginx git
   sudo adduser --system --group --home /srv/readymatch readymatch
   sudo usermod -aG www-data readymatch
   ```
2. **Base PostgreSQL**
   ```bash
   sudo -u postgres psql -c "CREATE USER readymatch WITH PASSWORD 'mot-de-passe-solide';"
   sudo -u postgres psql -c "CREATE DATABASE readymatch OWNER readymatch;"
   ```
3. **Code et dépendances** (dépôt Git ou copie du dossier dans `/srv/readymatch/app`)
   ```bash
   sudo -u readymatch git clone <votre-depot> /srv/readymatch/app
   cd /srv/readymatch/app
   sudo -u readymatch python3 -m venv .venv
   sudo -u readymatch .venv/bin/pip install -r requirements.txt
   ```
4. **Fichier `.env`** (à partir de `.env.example`)
   ```
   DJANGO_SECRET_KEY=<python3 -c "import secrets;print(secrets.token_urlsafe(64))">
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=readymatch.exemple.cm
   DJANGO_CSRF_TRUSTED_ORIGINS=https://readymatch.exemple.cm
   DATABASE_URL=postgres://readymatch:mot-de-passe-solide@127.0.0.1:5432/readymatch
   DJANGO_SECURE_SSL=True
   DJANGO_HSTS_SECONDS=0          # passer à 31536000 une fois le HTTPS vérifié
   ```
5. **Initialisation**
   ```bash
   sudo -u readymatch .venv/bin/python manage.py migrate
   sudo -u readymatch .venv/bin/python manage.py collectstatic --noinput
   sudo -u readymatch .venv/bin/python manage.py import_panaf "/chemin/ajouts_panaf_*.csv"
   sudo -u readymatch .venv/bin/python manage.py createsuperuser
   ```
6. **Service et Nginx**
   ```bash
   sudo cp deploy/readymatch.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable --now readymatch
   sudo cp deploy/nginx_readymatch.conf /etc/nginx/sites-available/readymatch   # remplacer le domaine
   sudo ln -s /etc/nginx/sites-available/readymatch /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d readymatch.exemple.cm
   ```
7. **Mises à jour** : `sudo bash /srv/readymatch/app/deploy/deploy.sh` (git pull, dépendances, migrations, fichiers statiques, redémarrage).

Les pièces de data room sont stockées dans `media/` et ne sont jamais servies en accès libre : l’application vérifie
les droits puis délègue l’envoi à Nginx (`X-Accel-Redirect`). Pensez à sauvegarder la base et le dossier `media/`.

## Site vitrine et appareils

- `templates/core/vitrine.html` : la page d’accueil, reprise à l’identique du prototype validé (site vitrine v3). En tête,
  l’accueil investisseur sans inscription ; les chiffres viennent de la base (`apps/core/services.py`, `apps/core/vitrine.py`).
  Styles : `static/css/vitrine.css` (chaque règle porte `:not(.app *)` pour ne jamais toucher les écrans des téléphones).
- « Essayez l’app » (`templates/core/_appareils.html`) : ordinateur, iPhone 17, Android (Galaxy S27 Ultra), Galaxy Z Flip 8
  et duo iPhone + Android. Les téléphones utilisent le moteur d’écrans du site vitrine v2 (`_appareils_ecrans.html`,
  `static/css/appareils_moteur.css`, `static/js/appareils.js`). L’ordinateur affiche les vrais écrans de l’application en lecture
  seule (`/apercu/pme/`, `/apercu/entreprises/`, `/apercu/fiche/`, `/apercu/pipeline/`), alimentés par `seed_demo`.
- L’ancienne landing simplifiée reste visible sur `/landing-simple/`.

## Écrans de chargement

`static/js/app.js` : barre de progression en haut de page et écran plein (logo animé + message) à chaque lien interne
ou formulaire ; message adapté avec `data-loader="…"`. Les filtres (entreprises, écosystème) se rechargent sans quitter
la page, avec des cartes squelettes pendant la requête (`<form data-async data-target="#zone">`).

## À compléter

- Cibles « entreprises rentables » et « projets réalisés sans investissement » : dans `config/settings.py`, `READYMATCH_CIBLES`.
- Conversion à 10 % contre 40 à 45 financements sur 600 entreprises : à mettre en cohérence.
- Inscription des structures d’accompagnement et des institutions, mise à niveau des preuves par un vérificateur,
  journal des accès à la data room, notifications par e-mail.
