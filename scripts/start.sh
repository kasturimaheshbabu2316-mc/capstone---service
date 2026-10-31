#!/usr/bin/env bash
# ==============================================================================
# Production Startup Script (Docker / Linux)
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================

set -e

PORT="${PORT:-8000}"
APP_MODE="${APP_MODE:-api}"

echo "===================================================================="
echo " Starting Ola Domain Support Intelligence Service"
echo " Mode: $APP_MODE | Port: $PORT"
echo "===================================================================="

echo "Launching FastAPI ASGI application..."
exec uvicorn api.main:app \
    --host 0.0.0.0 \
    --port "$PORT"
