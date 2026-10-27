# ==============================================================================
# Setup Script for Windows PowerShell
# Track: Business Operations / Customer Support (Ola)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Ola Support Intelligence — Local Environment Setup" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

# 1. Locate or create Python virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    py -3.11 -m venv .venv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path ".venv\Scripts\python.exe")) {
        python -m venv .venv
    }
} else {
    Write-Host "[1/4] Existing virtual environment found (.venv)." -ForegroundColor Green
}

$PyExe = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

# 2. Install requirements
Write-Host "[2/4] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $PyExe -m pip install --upgrade pip --quiet
& $PyExe -m pip install -r requirements.txt --quiet

# 3. Run model prefetch
Write-Host "[3/4] Running one-time model prefetch (sentence-transformers/all-MiniLM-L6-v2)..." -ForegroundColor Yellow
& $PyExe scripts/prefetch_models.py

# 4. Copy .env.example to .env if missing
Write-Host "[4/4] Verifying local configuration (.env)..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  -> Created .env from .env.example" -ForegroundColor Green
} else {
    Write-Host "  -> .env already present." -ForegroundColor Green
}

Write-Host "`n[+] Setup completed successfully!" -ForegroundColor Green
Write-Host "    Run '.\scripts\run_all.ps1' to verify and launch the service." -ForegroundColor Cyan
