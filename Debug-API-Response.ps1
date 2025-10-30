#!/usr/bin/env pwsh

Write-Host "Debugging API Response" -ForegroundColor Yellow

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
} | ConvertTo-Json -Depth 10

Write-Host "Request body:" -ForegroundColor Cyan
Write-Host $body

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/generate" -Method POST -Body $body -ContentType "application/json"
    
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response Content:" -ForegroundColor Cyan
    Write-Host $response.Content
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}

Write-Host "Done!" -ForegroundColor Green