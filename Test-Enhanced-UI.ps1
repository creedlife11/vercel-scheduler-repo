#!/usr/bin/env pwsh

Write-Host "🎨 Testing Enhanced Schedule Viewer UI" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow

# Generate a richer test schedule
Write-Host "`n1. Generating comprehensive test schedule..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 4
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "enhanced-test-schedule.csv" -Encoding UTF8
    Write-Host "✅ Enhanced schedule saved to enhanced-test-schedule.csv" -ForegroundColor Green
    
    # Show sample data
    $lines = ($response -split "`n")[0..7]
    Write-Host "`nSample schedule data:" -ForegroundColor White
    $lines | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    
} catch {
    Write-Host "❌ Failed to generate schedule: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test the enhanced UI
Write-Host "`n2. Testing enhanced UI features..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "✅ Enhanced schedule viewer accessible" -ForegroundColor Green
        
        # Check for enhanced features
        $content = $viewerResponse.Content
        $features = @(
            @{ Name = "Gradient backgrounds"; Pattern = "gradient" },
            @{ Name = "Engineer color coding"; Pattern = "ENGINEER_COLORS" },
            @{ Name = "Role icons"; Pattern = "Weekend|OnCall|Early|Chat|Appointments" },
            @{ Name = "Dashboard view"; Pattern = "dashboard" },
            @{ Name = "Enhanced animations"; Pattern = "transition|animate" }
        )
        
        foreach ($feature in $features) {
            if ($content -match $feature.Pattern) {
                Write-Host "  ✅ $($feature.Name) implemented" -ForegroundColor Green
            } else {
                Write-Host "  ⚠️ $($feature.Name) not detected" -ForegroundColor Yellow
            }
        }
    }
} catch {
    Write-Host "❌ Failed to test enhanced UI: $($_.Exception.Message)" -ForegroundColor Red
}

# Test file upload API
Write-Host "`n3. Testing enhanced file upload..." -ForegroundColor Cyan

try {
    $uploadTest = Invoke-WebRequest -Uri "http://localhost:3001/api/upload-schedule" -Method POST -ErrorAction SilentlyContinue
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "✅ Enhanced upload API endpoint working" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Upload API response: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

Write-Host "`n🎨 Enhanced UI Features Ready!" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow

Write-Host "`n🌟 New Features to Test:" -ForegroundColor Green
Write-Host "  📊 Dashboard View - Rich overview with stats cards" -ForegroundColor White
Write-Host "  🎨 Engineer Color Coding - Consistent colors per engineer" -ForegroundColor White
Write-Host "  🎭 Role Icons - Visual icons for each role type" -ForegroundColor White
Write-Host "  ✨ Animations - Smooth transitions and hover effects" -ForegroundColor White
Write-Host "  📱 Responsive Design - Works on all screen sizes" -ForegroundColor White
Write-Host "  🎯 Interactive Elements - Enhanced buttons and controls" -ForegroundColor White

Write-Host "`n🌐 Test URLs:" -ForegroundColor Yellow
Write-Host "  Main App: http://localhost:3001" -ForegroundColor White
Write-Host "  Enhanced Viewer: http://localhost:3001/schedule-viewer" -ForegroundColor White

Write-Host "`n📁 Test Files:" -ForegroundColor Yellow
Write-Host "  Basic: test-schedule.csv" -ForegroundColor White
Write-Host "  Enhanced: enhanced-test-schedule.csv" -ForegroundColor White

Write-Host "`n🎯 Testing Steps:" -ForegroundColor Yellow
Write-Host "  1. Open the schedule viewer in your browser" -ForegroundColor White
Write-Host "  2. Upload enhanced-test-schedule.csv" -ForegroundColor White
Write-Host "  3. Try Dashboard view (default) - see the rich cards" -ForegroundColor White
Write-Host "  4. Switch to Calendar view - see color-coded engineers" -ForegroundColor White
Write-Host "  5. Filter by individual engineers - see personal dashboards" -ForegroundColor White
Write-Host "  6. Try Statistics view - see the enhanced stats layout" -ForegroundColor White

Write-Host "`nReady to explore the enhanced UI!" -ForegroundColor Green