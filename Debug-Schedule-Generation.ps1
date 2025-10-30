# Debug what dates are being generated
$BaseUrl = "http://localhost:3001"

Write-Host "Debugging Schedule Generation" -ForegroundColor Cyan

$payload = @{
    engineers = @("Dan", "Mario", "Luigi", "Peach", "Yoshi", "Bowser")
    start_sunday = "2025-11-09"  # Sunday 09/11/2025
    weeks = 1  # Just 1 week to see what happens
    seeds = @{
        weekend = 0
        chat = 0
        oncall = 1
        appointments = 2
        early = 0
    }
    leave = @()
    format = "json"
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "SUCCESS! Generated $($response.schedule.Count) schedule entries" -ForegroundColor Green
    
    Write-Host "`nAll Generated Dates:" -ForegroundColor Yellow
    $response.schedule | Select-Object Date, Day, Weekend | Sort-Object Date | Format-Table -AutoSize
    
    Write-Host "`nExpected dates for 1 week starting Sunday 2025-11-09:" -ForegroundColor Cyan
    Write-Host "- Saturday 2025-11-08 (should be included for weekend pairing)"
    Write-Host "- Sunday 2025-11-09 (start date)"
    Write-Host "- Monday 2025-11-10"
    Write-Host "- Tuesday 2025-11-11"
    Write-Host "- Wednesday 2025-11-12"
    Write-Host "- Thursday 2025-11-13"
    Write-Host "- Friday 2025-11-14"
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"