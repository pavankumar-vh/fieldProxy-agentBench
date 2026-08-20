#!/bin/sh
# Container boot: migrate, seed once, serve.
set -e

echo "→ Applying migrations…"
alembic upgrade head

echo "→ Seeding if database is empty…"
python -m scripts.seed --if-empty

echo "→ Syncing LLM agent models…"
python -m scripts.sync_models

echo "→ Starting API on :8001…"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}"
