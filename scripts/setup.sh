#!/usr/bin/env bash
# ==============================================================================
# Setup Script for Linux & macOS
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================
set -e

echo "===================================================================="
echo " Ola Support Intelligence — Local Environment Setup"
echo "===================================================================="

# 1. Locate or create Python virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment (.venv)..."
    python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv || python -m venv .venv
else
    echo "[1/5] Existing virtual environment found (.venv)."
fi

if [ -f ".venv/bin/python" ]; then
    PY_EXE=".venv/bin/python"
else
    PY_EXE="python3"
fi

# Validate Python version: Python 3.11 or 3.12 (3.13+ not supported by this stack)
PY_MAJOR=$("$PY_EXE" -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$("$PY_EXE" -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 11 ] || [ "$PY_MINOR" -ge 13 ]; then
    echo "[ERROR] Python 3.11 or 3.12 (3.13+ not supported by this stack). Detected Python $PY_MAJOR.$PY_MINOR." >&2
    exit 1
fi

# 2. Install requirements
echo "[2/5] Installing dependencies from requirements.txt..."
"$PY_EXE" -m pip install --upgrade pip --quiet
"$PY_EXE" -m pip install -r requirements.txt --quiet

# 3. Run model prefetch
echo "[3/5] Running one-time model prefetch (sentence-transformers/all-MiniLM-L6-v2)..."
"$PY_EXE" scripts/prefetch_models.py

# 4. Ingest and index ChromaDB collections
echo "[4/5] Indexing policy documents into ChromaDB (rag/index.py)..."
"$PY_EXE" rag/index.py

# 5. Copy .env.example to .env if missing
echo "[5/5] Verifying local configuration (.env)..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  -> Created .env from .env.example"
else
    echo "  -> .env already present."
fi

echo ""
echo "[+] Setup completed successfully!"
echo "    Run './scripts/run_all.sh' to verify and launch the service."
