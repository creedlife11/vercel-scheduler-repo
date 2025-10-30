# Test OnCall exclusion logic
$BaseUrl = "http://localhost:3001"

Write-Host "Testing OnCall Exclusion Logic" -ForegroundColor Cyan
Write-Host "Expected:" -ForegroundColor Yellow
Write-Host "1. OnCall engineers should NOT be assigned to other weekday tasks (Chat, Appointments, Early)" -ForegroundColor Yellow
Write-Host "2. Previous week's OnCall engineer should NOT be assigned to following weekend" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
    weeks = 3  # Test 3 weeks to see exclusion patterns
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
    $response.schedule | Sort-Object Date | Select-Object Date, Day, Weekend, Chat, OnCall, Appointments, Early | Format-Table -AutoSize
    
    # Test 1: Check if OnCall engineers are assigned to other weekday tasks
    Write-Host "`nTest 1: OnCall Engineer Exclusion from Other Tasks" -ForegroundColor Cyan
    $weekdays = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" }
    $violations = @()
    
    foreach ($entry in $weekdays) {
        $onCallEng = $entry.OnCall
        $otherRoles = @()
        
        if ($entry.Chat -eq $onCallEng) { $otherRoles += "Chat" }
        if ($entry.Appointments -eq $onCallEng) { $otherRoles += "Appointments" }
        if ($entry.Early -eq $onCallEng) { $otherRoles += "Early" }
        
        if ($otherRoles.Count -gt 0) {
            $violations += "$($entry.Day) $($entry.Date): $onCallEng is OnCall AND $($otherRoles -join ', ')"
        }
    }
    
    if ($violations.Count -eq 0) {
        Write-Host "✅ PASS: No OnCall engineers assigned to other weekday tasks" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL: OnCall engineers assigned to other tasks:" -ForegroundColor Red
        $violations | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    
    # Test 2: Check if previous week's OnCall engineer is excluded from following weekend
    Write-Host "`nTest 2: Previous OnCall Engineer Weekend Exclusion" -ForegroundColor Cyan
    $weekends = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" } | Sort-Object Date
    
    # Get OnCall engineers by week
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
    
    Write-Host "OnCall Engineers by Week:" -ForegroundColor Magenta
    foreach ($week in $onCallByWeek.Keys | Sort-Object) {
        Write-Host "  Week ${week}: $($onCallByWeek[$week])"
    }
    
    Write-Host "`nWeekend Assignments:" -ForegroundColor Magenta
    foreach ($entry in $weekends) {
        Write-Host "  $($entry.Day) $($entry.Date): $($entry.Weekend)"
    }
    
    # Check for violations
    $weekendViolations = @()
    # Week 0 OnCall should not be assigned to Week 1 weekend
    if ($onCallByWeek.ContainsKey(0)) {
        $week0OnCall = $onCallByWeek[0]
        $week1Weekends = $weekends | Where-Object { 
            $date = [DateTime]::Parse($_.Date)
            $date -ge [DateTime]::Parse("2025-11-08") -and $date -le [DateTime]::Parse("2025-11-09")
        }
        foreach ($weekend in $week1Weekends) {
            if ($weekend.Weekend -eq $week0OnCall) {
                $weekendViolations += "Week 0 OnCall ($week0OnCall) assigned to $($weekend.Day) $($weekend.Date)"
            }
        }
    }
    
    if ($weekendViolations.Count -eq 0) {
        Write-Host "✅ PASS: Previous OnCall engineers not assigned to following weekend" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL: Previous OnCall engineers assigned to following weekend:" -ForegroundColor Red
        $weekendViolations | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"