@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo Starting Ola Support Intelligence (FastAPI Backend + Streamlit UI)
echo ====================================================================

:: Locate Python in .venv, .service, or PATH
set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else if exist ".service\Scripts\python.exe" (
    set "PY_EXE=.service\Scripts\python.exe"
)

echo [*] Using Python: %PY_EXE%

:: Set environment defaults
set "MOCK_LLM=true"
set "CREWAI_DISABLE_TELEMETRY=true"
set "BACKEND_URL=http://127.0.0.1:8000"

:: 1. Start FastAPI backend in background minimized window
echo [1/2] Starting FastAPI backend on http://127.0.0.1:8000...
start "Ola FastAPI Backend" /min "%PY_EXE%" -m uvicorn app.app:app --host 127.0.0.1 --port 8000

:: 2. Wait for backend /health check
echo [*] Waiting for FastAPI backend to initialize...
set "RETRIES=0"
:check_backend
"%PY_EXE%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" >nul 2>&1
if %errorlevel% neq 0 (
    set /a RETRIES+=1
    if !RETRIES! lss 8 (
        timeout /t 1 /nobreak >nul
        goto check_backend
    ) else (
        echo [!] Backend is still initializing, proceeding...
    )
) else (
    echo [*] Backend is healthy and responding at http://127.0.0.1:8000!
)

:: 3. Start Streamlit UI
echo [2/2] Starting Streamlit frontend on http://localhost:8501...
"%PY_EXE%" -m streamlit run streamlit_app.py --server.fileWatcherType none --server.port 8501
