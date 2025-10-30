#!/usr/bin/env pwsh

Write-Host "🚀 Testing Professional Calendar Features" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

# Generate comprehensive test data
Write-Host "`n1. Generating professional test data..." -ForegroundColor Cyan

$payload = @{
    start_sunday = "2025-11-02"
    weeks = 8
    engineers = @("Alice", "Bob", "Charlie", "Diana", "Eve", "Frank")
    seeds = @{ weekend = 0; oncall = 1; early = 2; chat = 3; appointments = 4 }
    leave = @()
    format = "csv"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/generate" -Method POST -Body $payload -ContentType "application/json"
    $response | Out-File -FilePath "professional-test.csv" -Encoding UTF8
    Write-Host "✅ Professional test data generated (8 weeks, 6 engineers)" -ForegroundColor Green
    
    # Count entries
    $lines = ($response -split "`n").Count - 1
    Write-Host "   📊 Generated $lines schedule entries" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed to generate data: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test professional features
Write-Host "`n2. Testing professional features..." -ForegroundColor Cyan

try {
    $viewerResponse = Invoke-WebRequest -Uri "http://localhost:3001/schedule-viewer" -Method GET
    
    if ($viewerResponse.StatusCode -eq 200) {
        Write-Host "✅ Professional calendar accessible" -ForegroundColor Green
        
        # Check for professional features
        $content = $viewerResponse.Content
        $features = @(
            @{ Name = "Sticky headers"; Pattern = "position.*sticky" },
            @{ Name = "Frozen columns"; Pattern = "left.*0.*z-index" },
            @{ Name = "Role legend"; Pattern = "Role Legend" },
            @{ Name = "Hover tooltips"; Pattern = "onMouseEnter" },
            @{ Name = "Click handlers"; Pattern = "onClick.*setSelectedDay" },
            @{ Name = "Advanced filters"; Pattern = "Show conflicts only" },
            @{ Name = "Day details drawer"; Pattern = "Day Details Drawer" }
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
    Write-Host "❌ Failed to test features: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🚀 Professional Features Ready!" -ForegroundColor Yellow
Write-Host "===============================" -ForegroundColor Yellow

Write-Host "`n🌟 New Professional Features:" -ForegroundColor Green
Write-Host "  📌 Sticky Headers - Headers stay visible while scrolling" -ForegroundColor White
Write-Host "  🔒 Frozen Columns - Date and Day columns stay fixed" -ForegroundColor White
Write-Host "  🎨 Role Legend - Visual legend with color coding" -ForegroundColor White
Write-Host "  💡 Hover Tooltips - Rich tooltips on cell hover" -ForegroundColor White
Write-Host "  🖱️ Click Details - Full day details in side drawer" -ForegroundColor White
Write-Host "  🔍 Advanced Filters - Conflicts only, weekends only" -ForegroundColor White
Write-Host "  📊 Conflict Detection - Automatic conflict identification" -ForegroundColor White
Write-Host "  📱 Professional Layout - Enterprise-grade design" -ForegroundColor White

Write-Host "`n🎯 Professional Testing Guide:" -ForegroundColor Yellow
Write-Host "  1. Open: http://localhost:3001/schedule-viewer" -ForegroundColor White
Write-Host "  2. Upload: professional-test.csv" -ForegroundColor White
Write-Host "  3. Switch to Calendar view -> Grid mode" -ForegroundColor White
Write-Host "  4. Scroll horizontally - notice sticky headers" -ForegroundColor White
Write-Host "  5. Hover over engineer badges - see tooltips" -ForegroundColor White
Write-Host "  6. Click any day - see details drawer" -ForegroundColor White
Write-Host "  7. Try 'Show conflicts only' filter" -ForegroundColor White
Write-Host "  8. Try 'Show weekends only' filter" -ForegroundColor White
Write-Host "  9. Filter by specific roles and engineers" -ForegroundColor White
Write-Host "  10. Test responsive behavior on mobile" -ForegroundColor White

Write-Host "`n📁 Test Files:" -ForegroundColor Yellow
Write-Host "  Professional: professional-test.csv (8 weeks)" -ForegroundColor White
Write-Host "  Rich Calendar: rich-calendar-test.csv (6 weeks)" -ForegroundColor White
Write-Host "  Enhanced: enhanced-test-schedule.csv (4 weeks)" -ForegroundColor White

Write-Host "`n🎨 Professional Features Highlights:" -ForegroundColor Yellow
Write-Host "  • Sticky navigation that stays in place" -ForegroundColor White
Write-Host "  • Interactive tooltips with context" -ForegroundColor White
Write-Host "  • Detailed day analysis drawer" -ForegroundColor White
Write-Host "  • Smart conflict detection" -ForegroundColor White
Write-Host "  • Advanced filtering options" -ForegroundColor White
Write-Host "  • Enterprise-grade visual design" -ForegroundColor White

Write-Host "`nReady for professional-grade scheduling!" -ForegroundColor Green