#!/usr/bin/env pwsh

Write-Host "Debugging Weekend Assignment Logic" -ForegroundColor Yellow
Write-Host "Expected: Each engineer should get fair weekend rotation, no consecutive weekends" -ForegroundColor Cyan

# Test the API with a simple scenario
$body = @{
    start_sunday = "2025-11-02"  # This is a Sunday
    weeks = 4
    engineers = @("Dan", "Dami", "Mario", "Mahmoud", "Prince", "Sherwin")
    seeds = @{
        weekend = 0
        oncall = 0
        early = 0
        chat = 0
        appointments = 0
    }
    leave = @()
    format = "json"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3000/api/generate" -Method POST -Body $body -ContentType "application/json"
    
    if ($response -and $response.schedule) {
        Write-Host "SUCCESS! Generated $($response.schedule.Count) schedule entries" -ForegroundColor Green
        Write-Host ""
        
        # Extract weekend assignments
        $weekendAssignments = @()
        foreach ($entry in $response.schedule) {
            $date = [DateTime]::Parse($entry.Date)
            if ($date.DayOfWeek -eq "Saturday" -or $date.DayOfWeek -eq "Sunday") {
                if ($entry.Weekend) {
                    $weekendAssignments += [PSCustomObject]@{
                        Date = $entry.Date
                        Day = $date.DayOfWeek
                        Engineer = $entry.Weekend
                        Week = if ($date.DayOfWeek -eq "Saturday") { 
                        # Saturday pairs with next day (Sunday)
                        $nextDay = $date.AddDays(1)
                        [Math]::Floor(($nextDay - [DateTime]::Parse("2025-11-02")).Days / 7)
                    } else { 
                        # Sunday
                        [Math]::Floor(($date - [DateTime]::Parse("2025-11-02")).Days / 7)
                    }
                    }
                }
            }
        }
        
        Write-Host "Weekend Assignments:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Date       Day      Engineer Week"
        Write-Host "----       ---      -------- ----"
        foreach ($assignment in $weekendAssignments) {
            Write-Host "$($assignment.Date) $($assignment.Day.ToString().PadRight(8)) $($assignment.Engineer.PadRight(8)) $($assignment.Week)"
        }
        
        Write-Host ""
        Write-Host "Weekend Analysis:" -ForegroundColor Yellow
        
        # Group by week to check weekend pairing
        $weekendsByWeek = $weekendAssignments | Group-Object Week
        foreach ($week in $weekendsByWeek) {
            $saturday = $week.Group | Where-Object { $_.Day -eq "Saturday" }
            $sunday = $week.Group | Where-Object { $_.Day -eq "Sunday" }
            
            if ($saturday -and $sunday) {
                if ($saturday.Engineer -eq $sunday.Engineer) {
                    Write-Host "Week $($week.Name): $($saturday.Engineer) (Saturday + Sunday) ✅ PAIRED" -ForegroundColor Green
                } else {
                    Write-Host "Week $($week.Name): $($saturday.Engineer) (Saturday) + $($sunday.Engineer) (Sunday) ❌ NOT PAIRED" -ForegroundColor Red
                }
            }
        }
        
        Write-Host ""
        Write-Host "Consecutive Weekend Check:" -ForegroundColor Yellow
        
        # Check for consecutive weekends
        $weekendWorkers = @{}
        foreach ($week in $weekendsByWeek) {
            $engineer = ($week.Group | Select-Object -First 1).Engineer
            if (-not $weekendWorkers.ContainsKey($engineer)) {
                $weekendWorkers[$engineer] = @()
            }
            $weekendWorkers[$engineer] += [int]$week.Name
        }
        
        foreach ($engineer in $weekendWorkers.Keys) {
            $weeks = $weekendWorkers[$engineer] | Sort-Object
            Write-Host "$engineer works weekends: $($weeks -join ', ')"
            
            # Check for consecutive weeks
            for ($i = 0; $i -lt $weeks.Count - 1; $i++) {
                if ($weeks[$i + 1] - $weeks[$i] -eq 1) {
                    Write-Host "  ❌ CONSECUTIVE: Week $($weeks[$i]) and Week $($weeks[$i + 1])" -ForegroundColor Red
                }
            }
        }
        
    } else {
        Write-Host "FAILED: No schedule data in response" -ForegroundColor Red
        Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green