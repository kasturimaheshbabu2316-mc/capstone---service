#!/usr/bin/env bash
set -e

echo "===================================================================="
echo " Ola Domain Support Intelligence — Production Startup"
echo "===================================================================="

# 1. Set environment variables
export MOCK_LLM="true"
export CREWAI_DISABLE_TELEMETRY="true"
export OTEL_SDK_DISABLED="true"
export PORT="${PORT:-8000}"
export PYTHONUNBUFFERED="1"

# Determine Python executable
if [ -f ".venv/bin/python" ]; then
    PY_EXE=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PY_EXE=".venv/Scripts/python.exe"
elif [ -f ".service/bin/python" ]; then
    PY_EXE=".service/bin/python"
elif [ -f ".service/Scripts/python.exe" ]; then
    PY_EXE=".service/Scripts/python.exe"
else
    PY_EXE="python3"
    if ! command -v "$PY_EXE" &>/dev/null; then
        PY_EXE="python"
    fi
fi

echo "[*] Using Python: $PY_EXE"

# 2. Run ingestion and ChromaDB indexing step
echo "[1/3] Running ingestion and ChromaDB indexing step..."
$PY_EXE rag/index.py

# 3. Start uvicorn (api.main:app --port 8000)
echo "[2/3] Starting uvicorn on port $PORT (api.main:app)..."
$PY_EXE -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT" &
UVICORN_PID=$!

cleanup() {
    echo ""
    echo "[*] Stopping uvicorn server (PID: $UVICORN_PID)..."
    kill $UVICORN_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 4. Wait for /health
echo "[3/3] Waiting for /health to respond..."
HEALTHY=0
for _ in {1..20}; do
    if $PY_EXE -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:${PORT}/health', timeout=1).getcode() == 200 else 1)" >/dev/null 2>&1; then
        echo "[*] Service is healthy! /health returned 200 OK."
        echo "[*] API is running at http://localhost:${PORT}"
        echo "[*] Swagger Docs at http://localhost:${PORT}/docs"
        HEALTHY=1
        break
    fi
    sleep 1
done

if [ $HEALTHY -eq 0 ]; then
    echo "[!] /health check timed out after 20 attempts."
    exit 1
fi

# Keep process alive
wait $UVICORN_PID
