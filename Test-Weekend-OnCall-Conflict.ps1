# Test for weekend + following week OnCall conflict
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekend + Following Week OnCall Conflict" -ForegroundColor Cyan
Write-Host "Expected: Engineer who does weekend should NOT do following week's OnCall" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
    weeks = 4  # Test 4 weeks to see the pattern
    seeds = @{
        weekend = 0
        chat = 0
        oncall = 1
        appointments = 2
        early = 3
    }
    leave = @()
    format = "json"
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "SUCCESS! Generated $($response.schedule.Count) schedule entries" -ForegroundColor Green
    
    # Get weekend and weekday entries
    $weekends = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" } | Sort-Object Date
    $weekdays = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" } | Sort-Object Date
    
    Write-Host "`nWeekend Assignments:" -ForegroundColor Yellow
    $weekends | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    Write-Host "`nWeekday OnCall by Week:" -ForegroundColor Cyan
    $onCallByWeek = @{}
    foreach ($entry in $weekdays) {
        $entryDate = [DateTime]::Parse($entry.Date)
        $weekStart = [DateTime]::Parse("2025-11-03") # First Monday
        $daysSinceStart = ($entryDate - $weekStart).Days
        $week = [Math]::Floor($daysSinceStart / 7)
        
        if (-not $onCallByWeek.ContainsKey($week)) {
            $onCallByWeek[$week] = $entry.OnCall
        }
    }
    
    foreach ($week in $onCallByWeek.Keys | Sort-Object) {
        Write-Host "Week ${week}: OnCall = $($onCallByWeek[$week])"
    }
    
    # Check for conflicts: Weekend engineer doing following week OnCall
    Write-Host "`nConflict Analysis:" -ForegroundColor Magenta
    $conflicts = @()
    
    # Group weekends by week
    $weekendPairs = @()
    for ($i = 0; $i -lt $weekends.Count; $i += 2) {
        if ($i + 1 -lt $weekends.Count) {
            $saturday = $weekends[$i]
            $sunday = $weekends[$i + 1]
            $weekNum = [Math]::Floor($i / 2)
            $weekendPairs += [PSCustomObject]@{
                Week = $weekNum
                Engineer = $saturday.Weekend
                SaturdayDate = $saturday.Date
                SundayDate = $sunday.Date
            }
        }
    }
    
    # Check each weekend against following week's OnCall
    foreach ($weekend in $weekendPairs) {
        $followingWeek = $weekend.Week + 1
        if ($onCallByWeek.ContainsKey($followingWeek)) {
            $followingOnCall = $onCallByWeek[$followingWeek]
            if ($weekend.Engineer -eq $followingOnCall) {
                $conflicts += "Week $($weekend.Week) weekend ($($weekend.Engineer)) + Week $followingWeek OnCall ($followingOnCall) = CONFLICT"
            } else {
                Write-Host "Week $($weekend.Week) weekend ($($weekend.Engineer)) + Week $followingWeek OnCall ($followingOnCall) = ✅ OK" -ForegroundColor Green
            }
        }
    }
    
    if ($conflicts.Count -eq 0) {
        Write-Host "✅ PASS: No weekend + following OnCall conflicts" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL: Weekend + following OnCall conflicts detected:" -ForegroundColor Red
        $conflicts | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"