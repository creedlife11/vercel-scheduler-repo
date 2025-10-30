# Test the specific weekend issue: 08/11/2025 Saturday Dan, 09/11/2025 Sunday Mario
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Specific Weekend Issue" -ForegroundColor Cyan
Write-Host "Expected: Same engineer for Saturday 08/11/2025 and Sunday 09/11/2025" -ForegroundColor Yellow

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
    
    # Find the specific weekend entries
    $saturday = $response.schedule | Where-Object { $_.Date -eq "2025-11-08" }
    $sunday = $response.schedule | Where-Object { $_.Date -eq "2025-11-09" }
    
    Write-Host "`nSpecific Weekend Analysis:" -ForegroundColor Magenta
    if ($saturday) {
        Write-Host "Saturday 08/11/2025: $($saturday.Weekend)" -ForegroundColor White
    } else {
        Write-Host "Saturday 08/11/2025: NOT FOUND" -ForegroundColor Red
    }
    
    if ($sunday) {
        Write-Host "Sunday 09/11/2025: $($sunday.Weekend)" -ForegroundColor White
    } else {
        Write-Host "Sunday 09/11/2025: NOT FOUND" -ForegroundColor Red
    }
    
    if ($saturday -and $sunday) {
        $match = if ($saturday.Weekend -eq $sunday.Weekend) { "✅ SAME ENGINEER" } else { "❌ DIFFERENT ENGINEERS" }
        Write-Host "Result: $match" -ForegroundColor $(if ($saturday.Weekend -eq $sunday.Weekend) { "Green" } else { "Red" })
    }
    
    # Show all weekend entries
    Write-Host "`nAll Weekend Entries:" -ForegroundColor Cyan
    $weekendEntries = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" }
    $weekendEntries | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"