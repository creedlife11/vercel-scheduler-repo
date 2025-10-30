# Test the exact scenario from user's data
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Exact User Scenario" -ForegroundColor Cyan
Write-Host "Expected: Mario should NOT do both Weekend 3 (15-16/11) AND Week 3 OnCall (17-21/11)" -ForegroundColor Yellow

$payload = @{
    engineers = @("Dan", "Mario", "Sherwin", "Dami", "Prince", "Mahmoud")
    start_sunday = "2025-11-02"  # Sunday 02/11/2025 (matches user data)
    weeks = 3  # Test 3 weeks to match user scenario
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
    
    Write-Host "`nComplete Schedule (matching user format):" -ForegroundColor Yellow
    $response.schedule | Sort-Object Date | Select-Object Date, Day, Weekend, Chat, OnCall, Appointments, Early | Format-Table -AutoSize
    
    # Focus on the specific conflict dates
    Write-Host "`nSpecific Conflict Analysis:" -ForegroundColor Cyan
    
    # Weekend 3: 15-16/11/2025
    $weekend3Sat = $response.schedule | Where-Object { $_.Date -eq "2025-11-15" }
    $weekend3Sun = $response.schedule | Where-Object { $_.Date -eq "2025-11-16" }
    
    # Week 3 OnCall: 17-21/11/2025
    $week3OnCall = $response.schedule | Where-Object { $_.Date -ge "2025-11-17" -and $_.Date -le "2025-11-21" } | Select-Object -First 1
    
    if ($weekend3Sat -and $weekend3Sun -and $week3OnCall) {
        $weekendEngineer = $weekend3Sat.Weekend
        $onCallEngineer = $week3OnCall.OnCall
        
        Write-Host "Weekend 3 (15-16/11): $weekendEngineer" -ForegroundColor White
        Write-Host "Week 3 OnCall (17-21/11): $onCallEngineer" -ForegroundColor White
        
        if ($weekendEngineer -eq $onCallEngineer) {
            Write-Host "❌ CONFLICT: $weekendEngineer does both Weekend 3 AND Week 3 OnCall!" -ForegroundColor Red
        } else {
            Write-Host "✅ OK: Different engineers for Weekend 3 and Week 3 OnCall" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠️ Could not find the specific dates to analyze" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`nDone!"