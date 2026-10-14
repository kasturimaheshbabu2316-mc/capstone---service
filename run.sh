#!/usr/bin/env bash
# ==============================================================================
# Unified Startup Script for Ola Support Intelligence (FastAPI + Streamlit)
# ==============================================================================
set -e

echo "===================================================================="
echo " Starting Ola Support Intelligence (FastAPI Backend + Streamlit UI)"
echo "===================================================================="

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
    PY_EXE="python"
fi

export MOCK_LLM="true"
export CREWAI_DISABLE_TELEMETRY="true"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

echo "[*] Using Python: $PY_EXE"

# 1. Start FastAPI backend in background
echo "[1/2] Starting FastAPI backend on http://127.0.0.1:8000..."
$PY_EXE -m uvicorn app.app:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Ensure FastAPI is gracefully stopped on script exit
cleanup() {
    echo ""
    echo "[*] Shutting down FastAPI backend (PID: $FASTAPI_PID)..."
    kill $FASTAPI_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 2. Wait for backend to be healthy
echo "[*] Waiting for FastAPI to initialize..."
for i in {1..10}; do
    if $PY_EXE -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" >/dev/null 2>&1; then
        echo "[*] Backend is healthy and responding at http://127.0.0.1:8000!"
        break
    fi
    sleep 1
done

# 3. Launch Streamlit frontend
echo "[2/2] Starting Streamlit frontend on http://localhost:8501..."
$PY_EXE -m streamlit run streamlit_app.py --server.fileWatcherType none --server.port 8501
