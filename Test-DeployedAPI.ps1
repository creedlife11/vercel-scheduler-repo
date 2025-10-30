# PowerShell script to test the deployed API
param(
    [string]$BaseUrl = "https://vercel-scheduler-repo-allv3zbkn-mikey-creeds-projects.vercel.app"
)

Write-Host "Testing Deployed Scheduler API" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Yellow

# Test payload
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

Write-Host "`nSending request..." -ForegroundColor Green
Write-Host "Payload: $payload" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "`nSUCCESS!" -ForegroundColor Green
    Write-Host "Schedule entries: $($response.schedule.Count)" -ForegroundColor Yellow
    Write-Host "Decision log entries: $($response.decisionLog.Count)" -ForegroundColor Yellow
    Write-Host "Generated at: $($response.metadata.generatedAt)" -ForegroundColor Yellow
    
    Write-Host "`nFirst few schedule entries:" -ForegroundColor Cyan
    $response.schedule | Select-Object -First 3 | Format-Table -AutoSize
    
    Write-Host "`nFairness Report:" -ForegroundColor Cyan
    $response.fairnessReport.engineerStats | Format-Table -AutoSize
    
    if ($response.decisionLog.Count -gt 0) {
        Write-Host "`nDecision Log (first 3 entries):" -ForegroundColor Cyan
        $response.decisionLog | Select-Object -First 3 | Format-List
    }
    
} catch {
    Write-Host "`nFAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        Write-Host "Status Description: $($_.Exception.Response.StatusDescription)" -ForegroundColor Red
    }
}

Write-Host "`nTesting feature flags endpoint..." -ForegroundColor Cyan

try {
    $features = Invoke-RestMethod -Uri "$BaseUrl/api/config/features" -Method GET -TimeoutSec 10
    Write-Host "Feature flags loaded successfully" -ForegroundColor Green
    Write-Host "Environment: $($features.environment)" -ForegroundColor Yellow
    Write-Host "Artifact Panel Enabled: $($features.features.enableArtifactPanel.enabled)" -ForegroundColor Yellow
    Write-Host "Leave Management Enabled: $($features.features.enableLeaveManagement.enabled)" -ForegroundColor Yellow
} catch {
    Write-Host "Feature flags failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTest completed!" -ForegroundColor Cyan