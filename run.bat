@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo  Ola Domain Support Intelligence — Production Startup
echo ====================================================================

:: 1. Set environment variables
set "MOCK_LLM=true"
set "CREWAI_DISABLE_TELEMETRY=true"
set "OTEL_SDK_DISABLED=true"
set "PORT=8000"
set "PYTHONUNBUFFERED=1"

:: Locate Python in .venv, .service, or PATH
set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else if exist ".service\Scripts\python.exe" (
    set "PY_EXE=.service\Scripts\python.exe"
)

echo [*] Using Python: %PY_EXE%

:: 2. Run ingestion and ChromaDB indexing step
echo [1/3] Running ingestion and ChromaDB indexing step...
"%PY_EXE%" rag\index.py
if %errorlevel% neq 0 (
    echo [!] Error during knowledge base indexing. Exiting.
    exit /b %errorlevel%
)

:: 3. Start uvicorn on port 8000
echo [2/3] Starting uvicorn on port 8000 (api.main:app)...
start "Ola Support API" "%PY_EXE%" -m uvicorn api.main:app --host 0.0.0.0 --port 8000

:: 4. Wait for /health
echo [3/3] Waiting for /health to respond...
set "RETRIES=0"
:check_health
"%PY_EXE%" -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=1).getcode() == 200 else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    set /a RETRIES+=1
    if !RETRIES! lss 20 (
        timeout /t 1 /nobreak >nul
        goto check_health
    ) else (
        echo [!] Healthcheck timed out after 20 seconds.
        exit /b 1
    )
) else (
    echo [*] Service is healthy! /health returned 200 OK.
    echo [*] API is running at http://localhost:8000
    echo [*] Swagger Docs at http://localhost:8000/docs
)
