#!/usr/bin/env pwsh

Write-Host "Testing Enhanced Schedule Viewer UI" -ForegroundColor Yellow

# Generate test schedule
Write-Host "1. Generating test schedule..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 4
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "enhanced-test-schedule.csv" -Encoding UTF8
    Write-Host "SUCCESS: Enhanced schedule saved" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test UI
Write-Host "2. Testing enhanced UI..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "SUCCESS: Enhanced UI accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Enhanced UI Features:" -ForegroundColor Green
Write-Host "- Dashboard View with stats cards" -ForegroundColor White
Write-Host "- Engineer color coding" -ForegroundColor White
Write-Host "- Role icons and animations" -ForegroundColor White
Write-Host "- Interactive elements" -ForegroundColor White

Write-Host ""
Write-Host "Test at: http://localhost:3001/schedule-viewer" -ForegroundColor Yellow
Write-Host "Upload: enhanced-test-schedule.csv" -ForegroundColor Yellow