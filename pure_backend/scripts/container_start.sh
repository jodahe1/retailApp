#!/usr/bin/env bash
set -euo pipefail

echo "[startup] waiting for postgres..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-retail_user}" -d "${POSTGRES_DB:-retail_db}" >/dev/null 2>&1; do
  sleep 1
done

echo "[startup] postgres is ready"
echo "[startup] running migrations"
alembic upgrade head

if [[ "${SEED_ON_START:-true}" == "true" ]]; then
  echo "[startup] running seed bootstrap"
  python -m scripts.seed_demo
fi

echo "[startup] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
