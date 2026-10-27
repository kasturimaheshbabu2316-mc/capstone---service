#!/usr/bin/env bash
# ==============================================================================
# Master Run & Verification Script for Linux & macOS
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================
set -e

echo "===================================================================="
echo " Ola Support Intelligence — Master Run & Local Launch"
echo "===================================================================="

# 1. Set environment variables
export MOCK_LLM="true"
export CREWAI_DISABLE_TELEMETRY="true"
export OTEL_SDK_DISABLED="true"
export HF_HUB_OFFLINE="1"
export TRANSFORMERS_OFFLINE="1"
export PORT="8000"

if [ -f ".venv/bin/python" ]; then
    PY_EXE=".venv/bin/python"
else
    PY_EXE="python3"
fi

# 2. Run pytest test suite
echo ""
echo "[1/4] Running test suite (pytest -q)..."
"$PY_EXE" -m pytest -q

# 3. Run benchmark evaluation
echo ""
echo "[2/4] Running 15-Query Evaluation Benchmark (evaluation/run_eval.py)..."
"$PY_EXE" evaluation/run_eval.py

# 4. Run AutoGen secondary review demo
echo ""
echo "[3/4] Running AutoGen Secondary Review Stage (review/autogen_review.py)..."
"$PY_EXE" review/autogen_review.py

# 5. Start uvicorn service
echo ""
echo "[4/4] Starting FastAPI backend on http://127.0.0.1:8000 ..."
echo "      • Dispatch Desk Console: http://127.0.0.1:8000"
echo "      • Interactive API Docs:  http://127.0.0.1:8000/docs"
echo "      • Health Check:          http://127.0.0.1:8000/health"
exec "$PY_EXE" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
