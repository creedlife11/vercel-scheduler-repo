# Simple PowerShell Testing Script
Write-Host "Testing Framework" -ForegroundColor Cyan

$PassedTests = 0
$FailedTests = 0

function Test-File {
    param([string]$Path, [string]$Description)
    
    $exists = Test-Path $Path
    if ($exists) {
        Write-Host "PASS $Description" -ForegroundColor Green
        $script:PassedTests++
    } else {
        Write-Host "FAIL $Description - Missing: $Path" -ForegroundColor Red
        $script:FailedTests++
    }
    return $exists
}

Write-Host "Testing Project Structure..." -ForegroundColor Yellow

# Test required files
Test-File "package.json" "Package configuration"
Test-File "pages\_app.tsx" "Next.js app component"
Test-File "pages\working-scheduler.tsx" "Emergency scheduler"
Test-File "pages\simple-index.tsx" "Simple landing page"
Test-File "pages\api\auth\[...nextauth].ts" "NextAuth API"
Test-File "pages\api\config\features.ts" "Features API"
Test-File "vercel.json" "Vercel configuration"
Test-File "next.config.js" "Next.js configuration"

Write-Host "Test Results:" -ForegroundColor Cyan
Write-Host "Passed: $PassedTests" -ForegroundColor Green
Write-Host "Failed: $FailedTests" -ForegroundColor Red

if ($FailedTests -eq 0) {
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed" -ForegroundColor Yellow
}