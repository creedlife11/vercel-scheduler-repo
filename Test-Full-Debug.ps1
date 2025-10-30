# Full debug test to see what's happening
$BaseUrl = "http://localhost:3001"

Write-Host "Full Debug Test" -ForegroundColor Cyan

$payload = @{
    engineers = @("Dan", "Mario", "Luigi", "Peach", "Yoshi", "Bowser")
    start_sunday = "2025-11-09"  # Sunday 09/11/2025
    weeks = 2
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
    
    Write-Host "`nFirst 5 schedule entries:" -ForegroundColor Yellow
    $response.schedule | Select-Object -First 5 | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    Write-Host "`nLast 5 schedule entries:" -ForegroundColor Yellow
    $response.schedule | Select-Object -Last 5 | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    Write-Host "`nAll dates in chronological order:" -ForegroundColor Cyan
    $response.schedule | Sort-Object Date | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    # Check for the specific Saturday
    $saturday = $response.schedule | Where-Object { $_.Date -eq "2025-11-08" }
    if ($saturday) {
        Write-Host "✅ Found Saturday 2025-11-08: $($saturday.Weekend)" -ForegroundColor Green
    } else {
        Write-Host "❌ Saturday 2025-11-08 NOT FOUND in schedule" -ForegroundColor Red
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"