# Test weekend pairing for the dates that are actually generated
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Weekend Pairing Logic" -ForegroundColor Cyan

$payload = @{
    engineers = @("Dan", "Mario", "Luigi", "Peach", "Yoshi", "Bowser")
    start_sunday = "2025-11-09"  # Sunday 09/11/2025
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
    
    # Get all weekend entries
    $weekendEntries = $response.schedule | Where-Object { $_.Day -eq "Saturday" -or $_.Day -eq "Sunday" }
    
    Write-Host "`nWeekend Assignments:" -ForegroundColor Yellow
    $weekendEntries | Sort-Object Date | Select-Object Date, Day, Weekend | Format-Table -AutoSize
    
    # Analyze weekend pairs
    Write-Host "`nWeekend Pairing Analysis:" -ForegroundColor Cyan
    
    # Group by calendar week (Saturday to Sunday)
    $weekendPairs = @()
    
    foreach ($entry in $weekendEntries) {
        $date = [DateTime]::Parse($entry.Date)
        $dayOfWeek = $date.DayOfWeek
        
        if ($dayOfWeek -eq [DayOfWeek]::Saturday) {
            # Find the Sunday of the same weekend (1 day later)
            $sundayDate = $date.AddDays(1).ToString("yyyy-MM-dd")
            $sunday = $weekendEntries | Where-Object { $_.Date -eq $sundayDate }
            
            if ($sunday) {
                $match = if ($entry.Weekend -eq $sunday.Weekend) { "✅ MATCH" } else { "❌ DIFFERENT" }
                Write-Host "Weekend: Saturday $($entry.Date) ($($entry.Weekend)) + Sunday $($sunday.Date) ($($sunday.Weekend)) = $match"
                $weekendPairs += @{
                    Saturday = $entry.Weekend
                    Sunday = $sunday.Weekend
                    Match = ($entry.Weekend -eq $sunday.Weekend)
                }
            } else {
                Write-Host "Weekend: Saturday $($entry.Date) ($($entry.Weekend)) + Sunday $sundayDate (NOT FOUND)"
            }
        }
    }
    
    $matchCount = ($weekendPairs | Where-Object { $_.Match }).Count
    $totalPairs = $weekendPairs.Count
    Write-Host "`nSummary: $matchCount out of $totalPairs weekend pairs match" -ForegroundColor $(if ($matchCount -eq $totalPairs) { "Green" } else { "Red" })
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"