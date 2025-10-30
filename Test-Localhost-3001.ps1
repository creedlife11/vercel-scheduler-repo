#!/usr/bin/env pwsh

Write-Host "Testing localhost:3001 API" -ForegroundColor Yellow

$body = @{
    start_sunday = "2025-11-02"
    weeks = 2
    engineers = @("Dan", "Dami", "Mario", "Mahmoud", "Prince", "Sherwin")
    seeds = @{
        weekend = 0
        oncall = 0
        early = 0
        chat = 0
        appointments = 0
    }
    leave = @()
    format = "json"
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Testing API endpoint..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $body -ContentType "application/json"
    
    if ($response -and $response.schedule) {
        Write-Host "✅ SUCCESS! API is working" -ForegroundColor Green
        Write-Host "Generated $($response.schedule.Count) schedule entries" -ForegroundColor Green
        
        # Show first few entries
        Write-Host "`nFirst 5 entries:" -ForegroundColor Cyan
        $response.schedule | Select-Object -First 5 | Format-Table Date, Day, Weekend, OnCall -AutoSize
        
    } else {
        Write-Host "❌ FAILED: No schedule data" -ForegroundColor Red
    }
    
    Write-Host "`nTesting web interface..." -ForegroundColor Cyan
    $webResponse = Invoke-WebRequest -Uri "http://localhost:3001" -Method GET
    if ($webResponse.StatusCode -eq 200) {
        Write-Host "✅ SUCCESS! Web interface is accessible" -ForegroundColor Green
    } else {
        Write-Host "❌ FAILED: Web interface returned status $($webResponse.StatusCode)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Response Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`n🌐 You can now access:" -ForegroundColor Yellow
Write-Host "   Main App: http://localhost:3001" -ForegroundColor White
Write-Host "   API Test: http://localhost:3001/test-api-direct.html" -ForegroundColor White
Write-Host "   Simple UI: http://localhost:3001/simple" -ForegroundColor White

Write-Host "`nDone!" -ForegroundColor Green