# Test weekly OnCall assignment over multiple weeks
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekly OnCall Assignment" -ForegroundColor Cyan
Write-Host "Expected: Same OnCall engineer for all weekdays of each week" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
    weeks = 3  # Test 3 weeks
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
    
    # Group by week and analyze OnCall assignments
    Write-Host "`nWeekly OnCall Analysis:" -ForegroundColor Cyan
    
    $weekdays = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" } | Sort-Object Date
    $weekends = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" } | Sort-Object Date
    
    # Analyze weekday OnCall by week
    $currentWeek = 1
    $weekStart = [DateTime]::Parse("2025-11-03") # First Monday
    
    Write-Host "`nWeekday OnCall Assignments:" -ForegroundColor Yellow
    foreach ($entry in $weekdays) {
        $entryDate = [DateTime]::Parse($entry.Date)
        $daysSinceStart = ($entryDate - $weekStart).Days
        $week = [Math]::Floor($daysSinceStart / 7) + 1
        
        if ($week -ne $currentWeek) {
            Write-Host ""
            $currentWeek = $week
        }
        
        Write-Host "Week $week - $($entry.Day) $($entry.Date): OnCall = $($entry.OnCall)"
    }
    
    Write-Host "`nWeekend OnCall Assignments:" -ForegroundColor Magenta
    foreach ($entry in $weekends) {
        Write-Host "$($entry.Day) $($entry.Date): Weekend = $($entry.Weekend), OnCall = $($entry.OnCall)"
    }
    
    # Verify weekly consistency
    Write-Host "`nWeekly Consistency Check:" -ForegroundColor Green
    $weeks = @{}
    foreach ($entry in $weekdays) {
        $entryDate = [DateTime]::Parse($entry.Date)
        $daysSinceStart = ($entryDate - $weekStart).Days
        $week = [Math]::Floor($daysSinceStart / 7) + 1
        
        if (-not $weeks.ContainsKey($week)) {
            $weeks[$week] = @()
        }
        $weeks[$week] += $entry.OnCall
    }
    
    foreach ($week in $weeks.Keys | Sort-Object) {
        $onCallEngineers = $weeks[$week] | Select-Object -Unique
        $consistent = if ($onCallEngineers.Count -eq 1) { "✅ CONSISTENT" } else { "❌ INCONSISTENT" }
        Write-Host "Week ${week}: OnCall = $($onCallEngineers -join ', ') - $consistent"
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"