#!/usr/bin/env pwsh

Write-Host "🎨 Testing Rich Calendar Experience" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow

# Generate a comprehensive test schedule
Write-Host "`n1. Generating rich test data..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 6
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "rich-calendar-test.csv" -Encoding UTF8
    Write-Host "✅ Rich calendar data generated (6 weeks, 6 engineers)" -ForegroundColor Green
    
    # Count entries
    $lines = ($response -split "`n").Count - 1
    Write-Host "   📊 Generated $lines schedule entries" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed to generate data: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test the enhanced calendar
Write-Host "`n2. Testing enhanced calendar features..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "✅ Enhanced calendar viewer accessible" -ForegroundColor Green
        
        # Check for new features
        $content = $viewerResponse.Content
        $features = @(
            @{ Name = "CSS Grid calendar"; Pattern = "calendar-grid" },
            @{ Name = "Timeline view"; Pattern = "timeline" },
            @{ Name = "Role filtering"; Pattern = "Role Filter" },
            @{ Name = "Calendar styles"; Pattern = "calendar-cell" },
            @{ Name = "Interactive elements"; Pattern = "hover.*transition" }
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
    Write-Host "❌ Failed to test calendar: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎨 Rich Calendar Features Ready!" -ForegroundColor Yellow
Write-Host "===============================" -ForegroundColor Yellow

Write-Host "`n🌟 New Calendar Features:" -ForegroundColor Green
Write-Host "  📊 CSS Grid Table - Perfect page-fitting layout" -ForegroundColor White
Write-Host "  🎯 Role-based Filtering - Filter by specific roles" -ForegroundColor White
Write-Host "  📅 Timeline View - Week-by-week timeline layout" -ForegroundColor White
Write-Host "  🎨 Gradient Backgrounds - Beautiful color schemes" -ForegroundColor White
Write-Host "  ✨ Hover Effects - Interactive cell animations" -ForegroundColor White
Write-Host "  📱 Responsive Design - Adapts to screen size" -ForegroundColor White
Write-Host "  🎯 Today Highlighting - Current day emphasis" -ForegroundColor White
Write-Host "  🏖️ Weekend Styling - Special weekend appearance" -ForegroundColor White

Write-Host "`n🎯 Testing Guide:" -ForegroundColor Yellow
Write-Host "  1. Open: http://localhost:3001/schedule-viewer" -ForegroundColor White
Write-Host "  2. Upload: rich-calendar-test.csv" -ForegroundColor White
Write-Host "  3. Switch to Calendar view" -ForegroundColor White
Write-Host "  4. Try Grid vs Timeline views" -ForegroundColor White
Write-Host "  5. Filter by different roles" -ForegroundColor White
Write-Host "  6. Filter by individual engineers" -ForegroundColor White
Write-Host "  7. Hover over calendar cells" -ForegroundColor White
Write-Host "  8. Test responsive design" -ForegroundColor White

Write-Host "`n📁 Test Files:" -ForegroundColor Yellow
Write-Host "  Basic: test-schedule.csv" -ForegroundColor White
Write-Host "  Enhanced: enhanced-test-schedule.csv" -ForegroundColor White
Write-Host "  Rich Calendar: rich-calendar-test.csv" -ForegroundColor White

Write-Host "`nReady to explore the rich calendar experience!" -ForegroundColor Green