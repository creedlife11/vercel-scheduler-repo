#!/usr/bin/env pwsh

Write-Host "Testing Rich Calendar Experience" -ForegroundColor Yellow

# Generate test data
Write-Host "1. Generating calendar test data..." -ForegroundColor Cyan

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
    $response | Out-File -FilePath "rich-calendar-test.csv" -Encoding UTF8
    Write-Host "SUCCESS: Rich calendar data generated" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test calendar
Write-Host "2. Testing calendar features..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "SUCCESS: Rich calendar accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Rich Calendar Features:" -ForegroundColor Green
Write-Host "- CSS Grid table layout" -ForegroundColor White
Write-Host "- Timeline view option" -ForegroundColor White
Write-Host "- Role-based filtering" -ForegroundColor White
Write-Host "- Interactive hover effects" -ForegroundColor White
Write-Host "- Responsive design" -ForegroundColor White
Write-Host "- Today highlighting" -ForegroundColor White

Write-Host ""
Write-Host "Test at: http://localhost:3001/schedule-viewer" -ForegroundColor Yellow
Write-Host "Upload: rich-calendar-test.csv" -ForegroundColor Yellow
Write-Host "Try: Calendar view -> Grid/Timeline toggle" -ForegroundColor Yellow