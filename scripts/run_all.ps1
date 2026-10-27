# ==============================================================================
# Master Run & Verification Script for Windows PowerShell
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Ola Support Intelligence — Master Run & Local Launch" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

# 1. Set environment variables
$env:MOCK_LLM = "true"
$env:CREWAI_DISABLE_TELEMETRY = "true"
$env:OTEL_SDK_DISABLED = "true"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PORT = "8000"

$PyExe = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

# 2. Run pytest test suite
Write-Host "`n[1/4] Running test suite (pytest -q)..." -ForegroundColor Yellow
& $PyExe -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Test suite failed. Exiting." -ForegroundColor Red
    exit 1
}

# 3. Run benchmark evaluation
Write-Host "`n[2/4] Running 15-Query Evaluation Benchmark (evaluation/run_eval.py)..." -ForegroundColor Yellow
& $PyExe evaluation/run_eval.py

# 4. Run AutoGen secondary review demo
Write-Host "`n[3/4] Running AutoGen Secondary Review Stage (review/autogen_review.py)..." -ForegroundColor Yellow
& $PyExe review/autogen_review.py

# 5. Start uvicorn service
Write-Host "`n[4/4] Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Write-Host "      • Dispatch Desk Console: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "      • Interactive API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "      • Health Check:          http://127.0.0.1:8000/health" -ForegroundColor Cyan
& $PyExe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
