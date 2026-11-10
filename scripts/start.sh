#!/usr/bin/env bash
# ==============================================================================
# Production Startup Script (Docker / Linux)
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================

set -e

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP_MODE="${APP_MODE:-api}"

echo "===================================================================="
echo " Starting Ola Domain Support Intelligence Service"
echo " Mode: $APP_MODE | Host: $HOST | Port: $PORT"
echo "===================================================================="

echo "Launching FastAPI ASGI application..."
exec uvicorn api.main:app \
    --host "$HOST" \
    --port "$PORT"
