#!/usr/bin/env bash
set -e

echo ">> Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

echo ">> Arrancando API en :8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
