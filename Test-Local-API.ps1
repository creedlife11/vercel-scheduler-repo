# Test the local development server
$BaseUrl = "http://localhost:3001"

Write-Host "Testing Local Scheduler API at: $BaseUrl"

$payload = @{
    engineers = @("Engineer A", "Engineer B", "Engineer C", "Engineer D", "Engineer E", "Engineer F")
    start_sunday = "2024-12-01"
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

Write-Host "Sending POST request to /api/generate..."

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "Schedule entries: $($response.schedule.Count)"
    Write-Host "Decision log entries: $($response.decisionLog.Count)"
    Write-Host "Generated at: $($response.metadata.generatedAt)"
    
    Write-Host "`nSample schedule entry:"
    $response.schedule[0] | Format-List
    
    Write-Host "`nFirst decision log entry:"
    if ($response.decisionLog.Count -gt 0) {
        $response.decisionLog[0] | Format-List
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
    
    if ($_.Exception.Response) {
        Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
    }
}

Write-Host "`nDone!"