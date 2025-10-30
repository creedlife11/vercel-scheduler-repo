#!/usr/bin/env pwsh

Write-Host "Testing Schedule Viewer Page" -ForegroundColor Yellow

try {
    Write-Host "Testing schedule viewer page..." -ForegroundColor Cyan
    $response = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ SUCCESS! Schedule viewer page is accessible" -ForegroundColor Green
        Write-Host "Page size: $($response.Content.Length) bytes" -ForegroundColor Green
        
        # Check if the page contains expected elements
        if ($response.Content -match "Schedule Viewer") {
            Write-Host "✅ Page title found" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Page title not found" -ForegroundColor Yellow
        }
        
        if ($response.Content -match "Upload.*CSV") {
            Write-Host "✅ CSV upload functionality detected" -ForegroundColor Green
        } else {
            Write-Host "⚠️ CSV upload functionality not detected" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ FAILED: Schedule viewer returned status $($response.StatusCode)" -ForegroundColor Red
    }
    
    Write-Host "`nTesting main page navigation..." -ForegroundColor Cyan
    $mainResponse = Invoke-WebRequest -Uri "http://localhost:3001" -Method GET
    
    if ($mainResponse.StatusCode -eq 200) {
        if ($mainResponse.Content -match "View Schedule") {
            Write-Host "✅ Navigation link found on main page" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Navigation link not found on main page" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Response Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`n🌐 You can now access:" -ForegroundColor Yellow
Write-Host "   Main App: http://localhost:3001" -ForegroundColor White
Write-Host "   Schedule Viewer: http://localhost:3001/schedule-viewer" -ForegroundColor White
Write-Host "   Sample CSV: sample-schedule.csv (in project root)" -ForegroundColor White

Write-Host "`nDone!" -ForegroundColor Green