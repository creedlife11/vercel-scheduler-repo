# Test weekly Early assignment with Chat/Appointments overlap
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekly Early Assignment" -ForegroundColor Cyan
Write-Host "Expected:" -ForegroundColor Yellow
Write-Host "1. One Early engineer assigned per week (like OnCall)" -ForegroundColor Yellow
Write-Host "2. Early engineer CAN also be assigned to Chat or Appointments" -ForegroundColor Yellow
Write-Host "3. OnCall engineer still CANNOT be assigned to other tasks" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
    weeks = 3  # Test 3 weeks
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
    
    Write-Host "`nComplete Weekday Schedule:" -ForegroundColor Yellow
    $weekdays = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" }
    $weekdays | Sort-Object Date | Select-Object Date, Day, Chat, OnCall, Appointments, Early | Format-Table -AutoSize
    
    # Test 1: Check Early engineer weekly consistency
    Write-Host "`nTest 1: Early Engineer Weekly Consistency" -ForegroundColor Cyan
    $earlyByWeek = @{}
    foreach ($entry in $weekdays) {
        $entryDate = [DateTime]::Parse($entry.Date)
        $weekStart = [DateTime]::Parse("2025-11-03") # First Monday
        $daysSinceStart = ($entryDate - $weekStart).Days
        $week = [Math]::Floor($daysSinceStart / 7)
        
        if (-not $earlyByWeek.ContainsKey($week)) {
            $earlyByWeek[$week] = @()
        }
        $earlyByWeek[$week] += $entry.Early
    }
    
    foreach ($week in $earlyByWeek.Keys | Sort-Object) {
        $earlyEngineers = $earlyByWeek[$week] | Select-Object -Unique
        $consistent = if ($earlyEngineers.Count -eq 1) { "✅ CONSISTENT" } else { "❌ INCONSISTENT" }
        Write-Host "Week ${week}: Early = $($earlyEngineers -join ', ') - $consistent"
    }
    
    # Test 2: Check if Early engineer can be assigned to Chat/Appointments
    Write-Host "`nTest 2: Early Engineer Multi-Role Assignment" -ForegroundColor Cyan
    $earlyMultiRole = @()
    foreach ($entry in $weekdays) {
        $earlyEng = $entry.Early
        $roles = @()
        
        if ($entry.Chat -eq $earlyEng) { $roles += "Chat" }
        if ($entry.Appointments -eq $earlyEng) { $roles += "Appointments" }
        
        if ($roles.Count -gt 0) {
            $earlyMultiRole += "$($entry.Day) $($entry.Date): $earlyEng is Early AND $($roles -join ', ')"
        }
    }
    
    if ($earlyMultiRole.Count -gt 0) {
        Write-Host "✅ GOOD: Early engineers can do other tasks:" -ForegroundColor Green
        $earlyMultiRole | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
    } else {
        Write-Host "⚠️ INFO: No Early engineers assigned to other tasks in this sample" -ForegroundColor Yellow
    }
    
    # Test 3: Verify OnCall engineers still exclusive
    Write-Host "`nTest 3: OnCall Engineer Exclusivity" -ForegroundColor Cyan
    $onCallViolations = @()
    foreach ($entry in $weekdays) {
        $onCallEng = $entry.OnCall
        $otherRoles = @()
        
        if ($entry.Chat -eq $onCallEng) { $otherRoles += "Chat" }
        if ($entry.Appointments -eq $onCallEng) { $otherRoles += "Appointments" }
        if ($entry.Early -eq $onCallEng) { $otherRoles += "Early" }
        
        if ($otherRoles.Count -gt 0) {
            $onCallViolations += "$($entry.Day) $($entry.Date): $onCallEng is OnCall AND $($otherRoles -join ', ')"
        }
    }
    
    if ($onCallViolations.Count -eq 0) {
        Write-Host "✅ PASS: OnCall engineers remain exclusive" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL: OnCall engineers assigned to other tasks:" -ForegroundColor Red
        $onCallViolations | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"