"""Configuration Gunicorn pour le VPS (lancée par systemd, derrière Nginx)."""
import multiprocessing

bind = 'unix:/run/ankadez/gunicorn.sock'
workers = min(max(2, multiprocessing.cpu_count() * 2 + 1), 5)   # plafonné pour garder de la mémoire sur un petit VPS
threads = 2
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
loglevel = 'info'
