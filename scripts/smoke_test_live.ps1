# ==============================================================================
# Live Deployment Smoke Test Script for Hugging Face Space / Production API
# Usage: .\scripts\smoke_test_live.ps1 -BaseUrl "https://<username>-ola-support-agent.hf.space"
# ==============================================================================

param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BaseUrl
)

$ErrorActionPreference = "Continue"
$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " LIVE DEPLOYMENT SMOKE TEST: $BaseUrl" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$testResults = [System.Collections.Generic.List[PSCustomObject]]::new()

# ------------------------------------------------------------------------------
# 1. Healthcheck with up to 12 retries (10s delay)
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 1: Checking /health (up to 12 retries, 10s delay for waking Spaces)..."
$healthOk = $false

for ($i = 1; $i -le 12; $i++) {
    Write-Host "    [Attempt $i/12] GET $BaseUrl/health ..."
    try {
        $res = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 10 -ErrorAction Stop
        if ($res.status -in @("healthy", "ok")) {
            $healthOk = $true
            Write-Host "    [+] Service is ready! Response:" -ForegroundColor Green
            $res | ConvertTo-Json | Write-Host
            break
        }
    } catch {
        Write-Host "    [-] Service not ready yet: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    if ($i -lt 12) {
        Start-Sleep -Seconds 10
    }
}

if (-not $healthOk) {
    Write-Host "    [!] Health check failed after 12 attempts." -ForegroundColor Red
    $testResults.Add([PSCustomObject]@{ Test = "1. Healthcheck (/health)"; Target = "status == ok/healthy"; Result = "FAIL" })
    Write-Host "`n[!] Aborting further tests because /health failed." -ForegroundColor Red
    $testResults | Format-Table -AutoSize
    exit 1
} else {
    $testResults.Add([PSCustomObject]@{ Test = "1. Healthcheck (/health)"; Target = "status == ok/healthy"; Result = "PASS" })
}

# ------------------------------------------------------------------------------
# 2. In-Scope RAG Query: Sev-1 SLA Question
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 2: In-Scope Policy Query (Sev-1 SLA)..."
$q1Passed = $false
try {
    $q1Body = @{
        session_id = "smoke_sev1"
        question   = "What is the resolution SLA for a Sev-1 safety incident?"
    } | ConvertTo-Json

    $q1Res = Invoke-RestMethod -Uri "$BaseUrl/ask" -Method Post -ContentType "application/json" -Body $q1Body -TimeoutSec 25 -ErrorAction Stop
    
    Write-Host "    • Answer:   $($q1Res.answer)" -ForegroundColor White
    Write-Host "    • Route:    $($q1Res.route)" -ForegroundColor Gray
    Write-Host "    • Grounded: $($q1Res.grounded)" -ForegroundColor Gray
    Write-Host "    • Trace ID: $($q1Res.trace_id)" -ForegroundColor Gray

    if ($q1Res.route -eq "rag" -and $q1Res.grounded -eq $true -and $q1Res.answer.Length -gt 15) {
        $q1Passed = $true
        Write-Host "    [+] In-scope policy response verified!" -ForegroundColor Green
    } else {
        Write-Host "    [-] In-scope validation criteria not met." -ForegroundColor Red
    }
} catch {
    Write-Host "    [-] Query error: $($_.Exception.Message)" -ForegroundColor Red
}
$testResults.Add([PSCustomObject]@{ Test = "2. In-Scope SLA Query"; Target = "route == rag, grounded == true"; Result = if ($q1Passed) { "PASS" } else { "FAIL" } })

# ------------------------------------------------------------------------------
# 3. Ticket Status Lookup (TKT-0007)
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 3: Ticket Status Lookup (TKT-0007)..."
$q2Passed = $false
try {
    $q2Body = @{
        session_id = "smoke_lookup"
        question   = "What is the status of ticket TKT-0007?"
    } | ConvertTo-Json

    $q2Res = Invoke-RestMethod -Uri "$BaseUrl/ask" -Method Post -ContentType "application/json" -Body $q2Body -TimeoutSec 25 -ErrorAction Stop
    
    Write-Host "    • Answer: $($q2Res.answer)" -ForegroundColor White
    Write-Host "    • Route:  $($q2Res.route)" -ForegroundColor Gray

    if ($q2Res.route -eq "lookup") {
        $q2Passed = $true
        Write-Host "    [+] Ticket lookup route verified!" -ForegroundColor Green
    } else {
        Write-Host "    [-] Expected route 'lookup', got '$($q2Res.route)'" -ForegroundColor Red
    }
} catch {
    Write-Host "    [-] Ticket lookup error: $($_.Exception.Message)" -ForegroundColor Red
}
$testResults.Add([PSCustomObject]@{ Test = "3. Ticket Lookup Query"; Target = "route == lookup (TKT-0007)"; Result = if ($q2Passed) { "PASS" } else { "FAIL" } })

# ------------------------------------------------------------------------------
# 4. Out-of-Scope Query Fallback
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 4: Out-of-Scope Query Fallback..."
$q3Passed = $false
try {
    $q3Body = @{
        session_id = "smoke_oos"
        question   = "Who won the cricket world cup?"
    } | ConvertTo-Json

    $q3Res = Invoke-RestMethod -Uri "$BaseUrl/ask" -Method Post -ContentType "application/json" -Body $q3Body -TimeoutSec 25 -ErrorAction Stop
    
    Write-Host "    • Answer:   $($q3Res.answer)" -ForegroundColor White
    Write-Host "    • Grounded: $($q3Res.grounded)" -ForegroundColor Gray

    if ($q3Res.answer -match "I don't know based on the available policy documents" -and $q3Res.grounded -eq $false) {
        $q3Passed = $true
        Write-Host "    [+] Calibrated refusal fallback verified!" -ForegroundColor Green
    } else {
        Write-Host "    [-] Expected exact refusal fallback text." -ForegroundColor Red
    }
} catch {
    Write-Host "    [-] Query error: $($_.Exception.Message)" -ForegroundColor Red
}
$testResults.Add([PSCustomObject]@{ Test = "4. Out-of-Scope Fallback"; Target = "exact I don't know fallback"; Result = if ($q3Passed) { "PASS" } else { "FAIL" } })

# ------------------------------------------------------------------------------
# 5. PII Masking: Ensure Fake Phone Number is Never Echoed
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 5: PII Phone Number Masking (98765 43210)..."
$q4Passed = $false
$fakePhone = "98765 43210"
try {
    $q4Body = @{
        session_id = "smoke_pii"
        question   = "Customer phone number $fakePhone requests policy details"
    } | ConvertTo-Json

    $q4Res = Invoke-RestMethod -Uri "$BaseUrl/ask" -Method Post -ContentType "application/json" -Body $q4Body -TimeoutSec 25 -ErrorAction Stop
    
    Write-Host "    • Answer: $($q4Res.answer)" -ForegroundColor White

    $hasRawPhone = ($q4Res.answer -match "98765 43210") -or ($q4Res.answer -match "9876543210")
    if (-not $hasRawPhone) {
        $q4Passed = $true
        Write-Host "    [+] Raw phone number was safely suppressed and never echoed!" -ForegroundColor Green
    } else {
        Write-Host "    [-] LEAK DETECTED: Raw phone number found in response!" -ForegroundColor Red
    }
} catch {
    Write-Host "    [-] Query error: $($_.Exception.Message)" -ForegroundColor Red
}
$testResults.Add([PSCustomObject]@{ Test = "5. PII Masking Protection"; Target = "no raw phone echoed"; Result = if ($q4Passed) { "PASS" } else { "FAIL" } })

# ------------------------------------------------------------------------------
# 6. Oversized Token Budget Check: Expect HTTP 413
# ------------------------------------------------------------------------------
Write-Host "`n[*] Test 6: Oversized Request (10,000 words, expect HTTP 413)..."
$oversizedPassed = $false
try {
    $hugeQuestion = "budgetlimit " * 10000
    $q5Body = @{
        session_id = "smoke_huge"
        question   = $hugeQuestion
    } | ConvertTo-Json

    $null = Invoke-RestMethod -Uri "$BaseUrl/ask" -Method Post -ContentType "application/json" -Body $q5Body -TimeoutSec 25 -ErrorAction Stop
    Write-Host "    [-] Error: Oversized query was unexpectedly accepted with HTTP 200!" -ForegroundColor Red
} catch {
    $status = 0
    if ($_.Exception.Response) {
        $status = [int]$_.Exception.Response.StatusCode
    }
    if ($status -eq 413 -or $_.Exception.Message -match "413") {
        $oversizedPassed = $true
        Write-Host "    [+] Successfully rejected with HTTP 413 Payload Too Large!" -ForegroundColor Green
    } else {
        Write-Host "    [-] Expected HTTP 413, received: $status ($($_.Exception.Message))" -ForegroundColor Red
    }
}
$testResults.Add([PSCustomObject]@{ Test = "6. Token Budget Enforcement"; Target = "HTTP 413 for oversized query"; Result = if ($oversizedPassed) { "PASS" } else { "FAIL" } })

# ------------------------------------------------------------------------------
# Final Summary Table & Exit Code
# ------------------------------------------------------------------------------
Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " LIVE SMOKE TEST FINAL RESULTS" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$testResults | Format-Table -AutoSize

$anyFailed = ($testResults | Where-Object { $_.Result -eq "FAIL" }).Count -gt 0
if ($anyFailed) {
    Write-Host "[!] One or more smoke tests FAILED. Exiting with code 1.`n" -ForegroundColor Red
    exit 1
} else {
    Write-Host "[+] All smoke tests PASSED successfully! Exiting with code 0.`n" -ForegroundColor Green
    exit 0
}
