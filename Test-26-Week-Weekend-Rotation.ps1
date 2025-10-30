# Test 26-week weekend rotation to identify the issue
$BaseUrl = "http://localhost:3001"

Write-Host "Testing 26-Week Weekend Rotation" -ForegroundColor Cyan
Write-Host "Expected: Fair rotation of weekend assignments across all engineers" -ForegroundColor Yellow

$payload = @{
    engineers = @("Engineer A", "Engineer B", "Engineer C", "Engineer D", "Engineer E", "Engineer F")
    start_sunday = "2025-01-05"  # Sunday start
    weeks = 26  # 26 weeks as reported
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
    Write-Host "Generating 26-week schedule..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 60
    
    Write-Host "SUCCESS! Generated $($response.schedule.Count) schedule entries" -ForegroundColor Green
    
    # Get all weekend entries
    $weekendEntries = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" } | Sort-Object Date
    
    Write-Host "`nWeekend Assignment Analysis:" -ForegroundColor Cyan
    Write-Host "Total weekend entries: $($weekendEntries.Count)" -ForegroundColor White
    
    # Count assignments by engineer
    $weekendCounts = @{}
    foreach ($entry in $weekendEntries) {
        if ($entry.Weekend) {
            if (-not $weekendCounts.ContainsKey($entry.Weekend)) {
                $weekendCounts[$entry.Weekend] = 0
            }
            $weekendCounts[$entry.Weekend]++
        }
    }
    
    Write-Host "`nWeekend Assignment Counts:" -ForegroundColor Yellow
    foreach ($engineer in $weekendCounts.Keys | Sort-Object) {
        $count = $weekendCounts[$engineer]
        $percentage = [Math]::Round(($count / $weekendEntries.Count) * 100, 1)
        Write-Host "$engineer : $count assignments ($percentage%)" -ForegroundColor White
    }
    
    # Check for fairness
    $maxAssignments = ($weekendCounts.Values | Measure-Object -Maximum).Maximum
    $minAssignments = ($weekendCounts.Values | Measure-Object -Minimum).Minimum
    $unfairness = $maxAssignments - $minAssignments
    
    Write-Host "`nFairness Analysis:" -ForegroundColor Magenta
    Write-Host "Max assignments: $maxAssignments" -ForegroundColor White
    Write-Host "Min assignments: $minAssignments" -ForegroundColor White
    Write-Host "Unfairness gap: $unfairness" -ForegroundColor $(if ($unfairness -le 2) { "Green" } else { "Red" })
    
    if ($unfairness -gt 10) {
        Write-Host "❌ CRITICAL ISSUE: Severe unfairness detected!" -ForegroundColor Red
    } elseif ($unfairness -gt 2) {
        Write-Host "⚠️ WARNING: Some unfairness detected" -ForegroundColor Yellow
    } else {
        Write-Host "✅ GOOD: Fair distribution" -ForegroundColor Green
    }
    
    # Show first 10 weekends to see the pattern
    Write-Host "`nFirst 10 Weekend Assignments:" -ForegroundColor Cyan
    $weekendEntries | Select-Object -First 20 | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    # Show pattern analysis
    Write-Host "`nWeekend Pattern Analysis:" -ForegroundColor Magenta
    $weekendPairs = @()
    for ($i = 0; $i -lt $weekendEntries.Count; $i += 2) {
        if ($i + 1 -lt $weekendEntries.Count) {
            $saturday = $weekendEntries[$i]
            $sunday = $weekendEntries[$i + 1]
            $weekNum = [Math]::Floor($i / 2) + 1
            $weekendPairs += [PSCustomObject]@{
                Week = $weekNum
                Saturday = $saturday.Weekend
                Sunday = $sunday.Weekend
                SaturdayDate = $saturday.Date
                SundayDate = $sunday.Date
            }
        }
    }
    
    Write-Host "First 10 Weekend Pairs:" -ForegroundColor Yellow
    $weekendPairs | Select-Object -First 10 | Format-Table -AutoSize
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"