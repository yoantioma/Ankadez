"""Réglages d’AnkadeZ. Tout ce qui change entre le poste local et le VPS se lit dans le fichier .env."""
import mimetypes
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

mimetypes.add_type('image/webp', '.webp')  # Windows ne connaît pas toujours le type des photos WebP

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'oui')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


DEBUG = env_bool('DJANGO_DEBUG', True)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-insecure-change-me' if DEBUG else '')
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY doit être défini en production.')
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'apps.accounts',
    'apps.annuaire',
    'apps.pme',
    'apps.investissement',
    'apps.offres',
    'apps.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.navigation',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
if _db_url.startswith('sqlite:///') and not Path(_db_url[len('sqlite:///'):]).is_absolute():
    # Un chemin SQLite relatif est résolu depuis le dossier du projet, quel que soit le dossier de lancement.
    _db_url = f'sqlite:///{(BASE_DIR / _db_url[len("sqlite:///"):]).as_posix()}'
DATABASES = {'default': dj_database_url.parse(_db_url, conn_max_age=60)}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = 'accounts:connexion'
LOGIN_REDIRECT_URL = 'core:espace'
LOGOUT_REDIRECT_URL = 'core:landing'

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / os.environ.get('DJANGO_STATIC_ROOT', 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / os.environ.get('DJANGO_MEDIA_ROOT', 'media')
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG
                    else 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sécurité en production (derrière Nginx en HTTPS)
if env_bool('DJANGO_SECURE_SSL', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO' if not DEBUG else 'WARNING'},
}

# Cibles à 36 mois arrêtées par le projet (affichées sur la landing, jamais additionnées aux chiffres réels)
ANKADEZ_CIBLES = {
    'entreprises_scorees': 600,
    'financements': '40 à 45',
    'montants_leves': '10 à 12 Md FCFA',
    'emplois': '≥ 2 000',
    'entreprises_rentables': None,       # à fixer
    'conversion_pct': 10,
    'projets_sans_investissement': None,  # à fixer
    'capital_cible_milieu_fcfa': 11_000_000_000,
}
