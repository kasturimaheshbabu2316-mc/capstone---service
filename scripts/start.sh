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

if [ "$APP_MODE" = "streamlit" ]; then
    echo "Launching Streamlit application..."
    exec streamlit run streamlit_app.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.headless true \
        --server.fileWatcherType none
else
    echo "Launching FastAPI ASGI application..."
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$PORT"
fi
