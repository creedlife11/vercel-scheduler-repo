#!/usr/bin/env pwsh

Write-Host "Testing Professional Calendar Features" -ForegroundColor Yellow

# Generate test data
Write-Host "1. Generating professional test data..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 8
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "professional-test.csv" -Encoding UTF8
    Write-Host "SUCCESS: Professional test data generated" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test features
Write-Host "2. Testing professional features..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "SUCCESS: Professional calendar accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Professional Features:" -ForegroundColor Green
Write-Host "- Sticky headers and frozen columns" -ForegroundColor White
Write-Host "- Role legend with color coding" -ForegroundColor White
Write-Host "- Hover tooltips for context" -ForegroundColor White
Write-Host "- Click for day details drawer" -ForegroundColor White
Write-Host "- Advanced filters (conflicts, weekends)" -ForegroundColor White
Write-Host "- Conflict detection system" -ForegroundColor White

Write-Host ""
Write-Host "Test at: http://localhost:3001/schedule-viewer" -ForegroundColor Yellow
Write-Host "Upload: professional-test.csv" -ForegroundColor Yellow
Write-Host "Try: Calendar view -> hover cells -> click days" -ForegroundColor Yellow