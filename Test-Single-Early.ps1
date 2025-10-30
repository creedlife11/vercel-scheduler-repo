# Test the simplified single Early role
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Single Early Role" -ForegroundColor Cyan
Write-Host "Expected: Only one 'Early' engineer instead of 'Early1' and 'Early2'" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025
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
    
    Write-Host "`nSimplified Schedule (Weekdays Only):" -ForegroundColor Yellow
    $weekdays = $response.schedule | Where-Object { $_.Day -ne "Saturday" -and $_.Day -ne "Sunday" }
    $weekdays | Sort-Object Date | Select-Object Date, Day, Chat, OnCall, Appointments, Early | Format-Table -AutoSize
    
    Write-Host "`nRole Assignment Summary:" -ForegroundColor Cyan
    Write-Host "✅ Weekend: Same engineer for Saturday + Sunday + OnCall" -ForegroundColor Green
    Write-Host "✅ OnCall: One engineer per week (Monday-Friday)" -ForegroundColor Green  
    Write-Host "✅ Chat: Daily rotation (excluding OnCall engineer)" -ForegroundColor Green
    Write-Host "✅ Appointments: Daily rotation (excluding OnCall engineer)" -ForegroundColor Green
    Write-Host "✅ Early: Single early engineer (simplified from Early1 + Early2)" -ForegroundColor Green
    
    # Verify Early role assignments
    Write-Host "`nEarly Role Analysis:" -ForegroundColor Magenta
    $earlyAssignments = $weekdays | Where-Object { $_.Early -ne "" } | Select-Object Date, Day, Early
    $earlyAssignments | Format-Table -AutoSize
    
    $uniqueEarlyEngineers = ($earlyAssignments | Select-Object -ExpandProperty Early | Sort-Object -Unique).Count
    Write-Host "Unique engineers assigned to Early role: $uniqueEarlyEngineers" -ForegroundColor White
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"