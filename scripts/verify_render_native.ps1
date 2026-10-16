# ==============================================================================
# Local Native Render Port 10000 Verification Script
# ==============================================================================

$OutputFile = "transcripts\18_render_prelaunch.txt"
$transcript = [System.Collections.Generic.List[string]]::new()

function Log-Message([string]$msg) {
    Write-Host $msg
    $script:transcript.Add($msg)
}

Log-Message "======================================================================"
Log-Message " RENDER PRE-LAUNCH NATIVE LOCAL VERIFICATION (PORT 10000)"
Log-Message " Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Log-Message "======================================================================"

$currentDir = (Get-Location).Path
$pythonExe = Join-Path $currentDir ".venv\Scripts\python.exe"

Log-Message "`n[*] Step 1: Starting Uvicorn natively on port 10000 (PORT=10000, MOCK_LLM=true)..."
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = $pythonExe
$pinfo.Arguments = "-m uvicorn api.main:app --host 0.0.0.0 --port 10000"
$pinfo.WorkingDirectory = $currentDir
$pinfo.UseShellExecute = $false
$pinfo.RedirectStandardOutput = $false
$pinfo.RedirectStandardError = $false
$pinfo.CreateNoWindow = $true
$pinfo.EnvironmentVariables["PORT"] = "10000"
$pinfo.EnvironmentVariables["MOCK_LLM"] = "true"
$pinfo.EnvironmentVariables["CREWAI_DISABLE_TELEMETRY"] = "true"
$pinfo.EnvironmentVariables["OTEL_SDK_DISABLED"] = "true"

$serverProc = [System.Diagnostics.Process]::Start($pinfo)

try {
    # 2. Wait for /health
    Log-Message "[*] Step 2: Polling http://localhost:10000/health ..."
    $healthOk = $false
    for ($i = 1; $i -le 15; $i++) {
        Start-Sleep -Seconds 2
        try {
            $hres = Invoke-RestMethod -Uri "http://localhost:10000/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
            if ($hres.status -in @("ok", "healthy")) {
                $healthOk = $true
                Log-Message "    [+] Health endpoint online! Response:"
                Log-Message ($hres | ConvertTo-Json -Compress)
                break
            }
        } catch {
            Log-Message "    [...] Waiting for startup (attempt $i/15)..."
        }
    }

    if (-not $healthOk) {
        throw "Failed to reach http://localhost:10000/health after 30 seconds."
    }

    # 3. Test /ask
    Log-Message "`n[*] Step 3: Testing POST http://localhost:10000/ask ..."
    $askPayload = @{
        question = "What is the resolution SLA for a Sev-1 safety incident?"
        session_id = "render_verify_001"
    } | ConvertTo-Json

    $askRes = Invoke-RestMethod -Uri "http://localhost:10000/ask" -Method Post -Body $askPayload -ContentType "application/json" -TimeoutSec 15
    Log-Message "    [+] POST /ask Response:"
    Log-Message "        Route:    $($askRes.route)"
    Log-Message "        Grounded: $($askRes.grounded)"
    Log-Message "        Answer:   $($askRes.answer)"
    Log-Message "        Trace ID: $($askRes.trace_id)"

} finally {
    Log-Message "`n[*] Shutting down native server process..."
    if ($serverProc -and -not $serverProc.HasExited) {
        $serverProc.Kill()
        $serverProc.WaitForExit(3000)
    }
}

# 4. Run pytest -q
Log-Message "`n[*] Step 4: Running full pytest test suite (pytest -q)..."
$pytestOutput = & $pythonExe -m pytest -q 2>&1
foreach ($line in $pytestOutput) {
    Log-Message $line
}

# 5. Save all transcript lines to transcripts\18_render_prelaunch.txt
Log-Message "`n======================================================================"
Log-Message " PRE-LAUNCH VERIFICATION COMPLETE"
Log-Message "======================================================================"
$script:transcript | Out-File -FilePath $OutputFile -Encoding utf8
Write-Host "`n[+] Transcript saved to $OutputFile" -ForegroundColor Green
