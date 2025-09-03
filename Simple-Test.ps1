# Simple PowerShell Testing Script
Write-Host "🧪 Simple Testing Framework" -ForegroundColor Cyan
Write-Host "="*50 -ForegroundColor Cyan

$PassedTests = 0
$FailedTests = 0

function Test-File {
    param([string]$Path, [string]$Description)
    
    $exists = Test-Path $Path
    if ($exists) {
        Write-Host "✅ $Description" -ForegroundColor Green
        $script:PassedTests++
    } else {
        Write-Host "❌ $Description - Missing: $Path" -ForegroundColor Red
        $script:FailedTests++
    }
    return $exists
}

function Test-Content {
    param([string]$Path, [string]$Pattern, [string]$Description)
    
    if (-not (Test-Path $Path)) {
        Write-Host "❌ $Description - File not found: $Path" -ForegroundColor Red
        $script:FailedTests++
        return $false
    }
    
    try {
        $content = Get-Content $Path -Raw
        $matches = $content -match $Pattern
        if ($matches) {
            Write-Host "✅ $Description" -ForegroundColor Green
            $script:PassedTests++
        } else {
            Write-Host "❌ $Description - Pattern not found: $Pattern" -ForegroundColor Red
            $script:FailedTests++
        }
        return $matches
    } catch {
        Write-Host "❌ $Description - Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:FailedTests++
        return $false
    }
}

Write-Host "`n📁 Testing Project Structure..." -ForegroundColor Yellow

# Test required files
Test-File "package.json" "Package configuration"
Test-File "pages\_app.tsx" "Next.js app component"
Test-File "pages\working-scheduler.tsx" "Emergency scheduler"
Test-File "pages\simple-index.tsx" "Simple landing page"
Test-File "pages\api\auth\[...nextauth].ts" "NextAuth API"
Test-File "pages\api\config\features.ts" "Features API"
Test-File "vercel.json" "Vercel configuration"
Test-File "next.config.js" "Next.js configuration"

Write-Host "`n📝 Testing File Contents..." -ForegroundColor Yellow

# Test emergency scheduler functionality
Test-Content "pages\working-scheduler.tsx" "export default" "Emergency scheduler export"
Test-Content "pages\working-scheduler.tsx" "useState" "React state management"
Test-Content "pages\working-scheduler.tsx" "generateSchedule" "Schedule generation function"
Test-Content "pages\working-scheduler.tsx" "downloadCSV" "CSV download function"

# Test package.json
Test-Content "package.json" '"next"' "Next.js dependency"
Test-Content "package.json" '"react"' "React dependency"
Test-Content "package.json" '"build"' "Build script"

# Test NextAuth
Test-Content "pages\api\auth\[...nextauth].ts" "NextAuth" "NextAuth import"
Test-Content "pages\api\auth\[...nextauth].ts" "CredentialsProvider" "Credentials provider"

Write-Host "`n📊 Test Results:" -ForegroundColor Cyan
Write-Host "Passed: $PassedTests" -ForegroundColor Green
Write-Host "Failed: $FailedTests" -ForegroundColor Red

$total = $PassedTests + $FailedTests
if ($total -gt 0) {
    $successRate = [math]::Round(($PassedTests / $total) * 100, 1)
    Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } else { "Yellow" })
}

if ($FailedTests -eq 0) {
    Write-Host "`n🎉 ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n⚠️  Some tests failed, but deployment may still work" -ForegroundColor Yellow
    exit 1
}