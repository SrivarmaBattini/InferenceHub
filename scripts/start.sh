#!/usr/bin/env bash
# scripts/start.sh — production startup

set -euo pipefail   # exit on any error

echo "=== InferenceHub startup ==="

# ── Validate environment ───────────────────────────────────────────────────────
required_vars=(DATABASE_URL REDIS_URL SECRET_KEY)
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# ── Run migrations ─────────────────────────────────────────────────────────────
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete"

# ── Train model if not present ─────────────────────────────────────────────────
if [[ ! -f "ml_models/regressor_v1.joblib" ]]; then
    echo "Model not found — training..."
    python scripts/train_model.py
fi

# ── Start server ───────────────────────────────────────────────────────────────
echo "Starting Gunicorn with ${GUNICORN_WORKERS:-4} workers..."
exec gunicorn main:app -c gunicorn.conf.py
