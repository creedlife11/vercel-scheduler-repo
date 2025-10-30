# Test weekend assignment logic specifically
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekend Assignment Logic" -ForegroundColor Cyan

$payload = @{
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    start_sunday = "2024-12-01"  # Sunday
    weeks = 3  # Test 3 weeks to see rotation
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
    
    # Filter weekend entries
    $weekendEntries = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" }
    
    Write-Host "`nWeekend Assignments:" -ForegroundColor Yellow
    $weekendEntries | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    # Check weekend pairs
    Write-Host "`nWeekend Pairs Analysis:" -ForegroundColor Cyan
    for ($week = 0; $week -lt 3; $week++) {
        $weekStart = (Get-Date "2024-12-01").AddDays($week * 7)
        $saturday = $weekStart.AddDays(6).ToString("yyyy-MM-dd")
        $sunday = $weekStart.ToString("yyyy-MM-dd")
        
        $satEntry = $response.schedule | Where-Object { $_.Date -eq $saturday }
        $sunEntry = $response.schedule | Where-Object { $_.Date -eq $sunday }
        
        if ($satEntry -and $sunEntry) {
            $match = if ($satEntry.Weekend -eq $sunEntry.Weekend) { "✅ MATCH" } else { "❌ DIFFERENT" }
            Write-Host "Week $($week + 1): Saturday ($saturday) = $($satEntry.Weekend), Sunday ($sunday) = $($sunEntry.Weekend) - $match"
        }
    }
    
    # Show weekend decision log entries
    $weekendDecisions = $response.decisionLog | Where-Object { $_.decision_type -eq "weekend_assignment" }
    Write-Host "`nWeekend Decision Log Entries: $($weekendDecisions.Count)" -ForegroundColor Magenta
    $weekendDecisions | Select-Object date, affected_engineers, reason | Format-Table -AutoSize
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"