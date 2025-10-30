# Test weekend OnCall assignment
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekend OnCall Assignment" -ForegroundColor Cyan
Write-Host "Expected: Weekend engineer should also be OnCall for Saturday and Sunday" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
    weeks = 1
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
    
    Write-Host "`nComplete Schedule:" -ForegroundColor Yellow
    $response.schedule | Sort-Object Date | Select-Object Date, Day, Weekend, Chat, OnCall, Appointments, Early1, Early2 | Format-Table -AutoSize
    
    # Check weekend OnCall assignments
    Write-Host "`nWeekend OnCall Analysis:" -ForegroundColor Cyan
    $weekendEntries = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" }
    
    foreach ($entry in $weekendEntries) {
        $match = if ($entry.Weekend -eq $entry.OnCall) { "✅ MATCH" } else { "❌ DIFFERENT" }
        Write-Host "$($entry.Day) $($entry.Date): Weekend=$($entry.Weekend), OnCall=$($entry.OnCall) - $match"
    }
    
    # Check weekday OnCall assignments
    Write-Host "`nWeekday OnCall Analysis:" -ForegroundColor Magenta
    $weekdayEntries = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" }
    
    foreach ($entry in $weekdayEntries) {
        Write-Host "$($entry.Day) $($entry.Date): OnCall=$($entry.OnCall)"
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"