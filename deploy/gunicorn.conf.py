"""Configuration Gunicorn pour le VPS (lancée par systemd, derrière Nginx)."""
import multiprocessing

bind = 'unix:/run/readymatch/gunicorn.sock'
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
threads = 2
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
loglevel = 'info'
