# AnkadeZ · image de l'application Django (Gunicorn)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Africa/Douala

WORKDIR /app

# Dépendances d'abord (mise en cache des couches Docker)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code de l'application
COPY . .

# Utilisateur non root ; les dossiers des volumes lui appartiennent dès la création
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/staticfiles /app/media /app/donnees \
    && chown -R app:app /app \
    && chmod +x /app/docker/entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
