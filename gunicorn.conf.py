# gunicorn.conf.py
import multiprocessing
import os

# ── Worker count ───────────────────────────────────────────────────────────────
# Read from env (set in docker compose), fall back to formula
workers = int(
    os.getenv(
        "GUNICORN_WORKERS",
        str(multiprocessing.cpu_count() * 2 + 1),
    )
)

# ── Worker class ───────────────────────────────────────────────────────────────
# UvicornWorker bridges Gunicorn process management with Uvicorn's ASGI runtime
worker_class = "uvicorn.workers.UvicornWorker"

# ── Binding ────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# ── Timeouts ───────────────────────────────────────────────────────────────────
# Time to wait for a worker to handle a request before killing it
# ML inference can be slow — set this higher than your worst-case prediction time
timeout        = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Time to wait for in-flight requests to complete on graceful shutdown
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# How long to wait for a worker to boot before giving up
worker_init_timeout = 30

# ── Connection handling ────────────────────────────────────────────────────────
# Max simultaneous clients per worker (async workers handle many per coroutine)
worker_connections = 1000

# Max requests before worker is restarted — prevents memory leaks
max_requests      = int(os.getenv("GUNICORN_MAX_REQUESTS",      "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
# Jitter prevents all workers restarting simultaneously

# ── Logging ───────────────────────────────────────────────────────────────────
# "-" means stdout — captured by Docker logs
accesslog  = "-"
errorlog   = "-"
loglevel   = os.getenv("GUNICORN_LOG_LEVEL", "info")

# ── Process naming ─────────────────────────────────────────────────────────────
proc_name = "inferencehub"

# ── Security ───────────────────────────────────────────────────────────────────
# Prevent slowloris attacks — close connections that send headers slowly
limit_request_line   = 4096   # max URL length in bytes
limit_request_fields = 100    # max number of headers

# ── Hooks — run code at worker lifecycle events ────────────────────────────────
def on_starting(server):
    """Called when the master process starts."""
    server.log.info("InferenceHub starting up")

def worker_int(worker):
    """Called when a worker receives SIGINT (ctrl+c)."""
    worker.log.info(f"Worker {worker.pid} received SIGINT — shutting down")

def worker_exit(server, worker):
    """Called after a worker exits."""
    server.log.info(f"Worker {worker.pid} exited")

def post_fork(server, worker):
    """Called in each worker after fork — good for per-worker setup."""
    server.log.info(f"Worker {worker.pid} spawned")
