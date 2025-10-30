#!/usr/bin/env pwsh

Write-Host "Testing Calendar-Style Interface" -ForegroundColor Yellow

# Generate comprehensive test data
Write-Host "1. Generating calendar-style test data..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 6
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "calendar-style-test.csv" -Encoding UTF8
    Write-Host "SUCCESS: Calendar-style test data generated" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test calendar interface
Write-Host "2. Testing calendar-style interface..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "SUCCESS: Calendar-style interface accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Calendar-Style Features:" -ForegroundColor Green
Write-Host "- Full-screen professional calendar view" -ForegroundColor White
Write-Host "- React Big Calendar integration" -ForegroundColor White
Write-Host "- Resource timeline view" -ForegroundColor White
Write-Host "- Day/Week/Month view modes" -ForegroundColor White
Write-Host "- Mobile-responsive design" -ForegroundColor White
Write-Host "- Interactive event clicking" -ForegroundColor White
Write-Host "- Today highlighting" -ForegroundColor White
Write-Host "- Weekend emphasis" -ForegroundColor White

Write-Host ""
Write-Host "Test at: http://localhost:3001/schedule-viewer" -ForegroundColor Yellow
Write-Host "Upload: calendar-style-test.csv" -ForegroundColor Yellow
Write-Host "Try: Calendar view -> Day/Week/Month modes" -ForegroundColor Yellow
Write-Host "Try: Timeline view -> Resource overview" -ForegroundColor Yellow