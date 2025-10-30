#!/usr/bin/env pwsh

Write-Host "Testing Schedule Viewer" -ForegroundColor Yellow

# Test 1: Generate a schedule
Write-Host "1. Generating test schedule..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 3
    engineers = @("Dan", "Dami", "Mario", "Mahmoud", "Prince", "Sherwin")
    seeds = @{ weekend = 0; oncall = 0; early = 0; chat = 0; appointments = 0 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "test-schedule.csv" -Encoding UTF8
    Write-Host "SUCCESS: Schedule saved to test-schedule.csv" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Check schedule viewer page
Write-Host "2. Testing schedule viewer page..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "SUCCESS: Schedule viewer page accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Ready to test!" -ForegroundColor Green
Write-Host "Open: http://localhost:3001/schedule-viewer" -ForegroundColor White
Write-Host "Upload: test-schedule.csv" -ForegroundColor White