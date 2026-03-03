"""
Gunicorn Configuration - Memory Optimized for Minibar Takip
"""
import multiprocessing
import os

# Server Socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker Processes - CAPACITY OPTIMIZED (03.03.2026)
# 8.3 GB RAM, düşük CPU kullanımı - daha fazla worker kaldırır
# preload_app: App'i master process'te 1 kez yükle, worker'lar fork ile hazır alsın
preload_app = True
workers = int(os.getenv('GUNICORN_WORKERS', '3'))  # 3 worker (8GB RAM rahat kaldırır)
worker_class = 'gthread'  # gthread worker (thread destekli)
threads = int(os.getenv('GUNICORN_THREADS', '6'))  # 6 threads per worker = 18 eşzamanlı istek
worker_connections = 1000
max_requests = int(os.getenv('MAX_REQUESTS', '1000'))  # 1000 request'te worker recycle
max_requests_jitter = int(os.getenv('MAX_REQUESTS_JITTER', '100'))  # Thundering herd önleme

# Template Reload - Production'da bile template değişikliklerini algıla
reload = os.getenv('GUNICORN_RELOAD', 'false').lower() == 'true'
reload_extra_files = []  # Template dosyaları için (isteğe bağlı)

# Timeouts
timeout = int(os.getenv('GUNICORN_TIMEOUT', '300'))  # 300s default (app import ~120s sürüyor)
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = 'minibar-takip'

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Memory Management Hooks
def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker received INT or QUIT signal (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker received SIGABRT signal (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info(f"Worker exited (pid: {worker.pid})")

# Memory limit için worker restart
def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    pass
