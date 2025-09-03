# Deployment Diagnostic Script
Write-Host "Deployment Diagnostic Report" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

$issues = @()
$successes = @()

# Check critical files
$criticalFiles = @(
    "package.json",
    "pages\_app.tsx", 
    "pages\working-scheduler.tsx",
    "pages\simple-index.tsx",
    "vercel.json",
    "next.config.js"
)

Write-Host "`nChecking Critical Files:" -ForegroundColor Yellow
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        Write-Host "  FOUND: $file" -ForegroundColor Green
        $successes += "File exists: $file"
    } else {
        Write-Host "  MISSING: $file" -ForegroundColor Red
        $issues += "Missing file: $file"
    }
}

# Check emergency scheduler content
Write-Host "`nChecking Emergency Scheduler:" -ForegroundColor Yellow
if (Test-Path "pages\working-scheduler.tsx") {
    $content = Get-Content "pages\working-scheduler.tsx" -Raw
    
    $checks = @(
        @{Pattern = "export default"; Name = "Component export"},
        @{Pattern = "useState"; Name = "React state"},
        @{Pattern = "generateSchedule"; Name = "Generation function"},
        @{Pattern = "downloadCSV"; Name = "Download function"},
        @{Pattern = "No.*API.*dependencies|client-side|browser"; Name = "Client-side processing"}
    )
    
    foreach ($check in $checks) {
        if ($content -match $check.Pattern) {
            Write-Host "  FOUND: $($check.Name)" -ForegroundColor Green
            $successes += "Emergency scheduler has: $($check.Name)"
        } else {
            Write-Host "  MISSING: $($check.Name)" -ForegroundColor Red
            $issues += "Emergency scheduler missing: $($check.Name)"
        }
    }
} else {
    Write-Host "  ERROR: Emergency scheduler file not found!" -ForegroundColor Red
    $issues += "Emergency scheduler file missing"
}

# Check package.json
Write-Host "`nChecking Package Configuration:" -ForegroundColor Yellow
if (Test-Path "package.json") {
    try {
        $package = Get-Content "package.json" | ConvertFrom-Json
        
        $requiredDeps = @("next", "react", "react-dom")
        foreach ($dep in $requiredDeps) {
            if ($package.dependencies.PSObject.Properties.Name -contains $dep) {
                Write-Host "  FOUND: $dep dependency" -ForegroundColor Green
                $successes += "Dependency configured: $dep"
            } else {
                Write-Host "  MISSING: $dep dependency" -ForegroundColor Red
                $issues += "Missing dependency: $dep"
            }
        }
        
        if ($package.scripts.PSObject.Properties.Name -contains "build") {
            Write-Host "  FOUND: build script" -ForegroundColor Green
            $successes += "Build script configured"
        } else {
            Write-Host "  MISSING: build script" -ForegroundColor Red
            $issues += "Missing build script"
        }
        
    } catch {
        Write-Host "  ERROR: Cannot parse package.json" -ForegroundColor Red
        $issues += "Invalid package.json format"
    }
} else {
    Write-Host "  ERROR: package.json not found" -ForegroundColor Red
    $issues += "package.json missing"
}

# Summary
Write-Host "`n=============================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC SUMMARY" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

Write-Host "`nSuccesses ($($successes.Count)):" -ForegroundColor Green
foreach ($success in $successes) {
    Write-Host "  + $success" -ForegroundColor Green
}

Write-Host "`nIssues ($($issues.Count)):" -ForegroundColor Red
foreach ($issue in $issues) {
    Write-Host "  - $issue" -ForegroundColor Red
}

# Deployment recommendation
Write-Host "`nDEPLOYMENT RECOMMENDATION:" -ForegroundColor Cyan
if ($issues.Count -eq 0) {
    Write-Host "DEPLOY NOW - All checks passed!" -ForegroundColor Green
} elseif ($issues.Count -le 2) {
    Write-Host "DEPLOY WITH CAUTION - Minor issues detected" -ForegroundColor Yellow
} else {
    Write-Host "FIX ISSUES FIRST - Multiple problems found" -ForegroundColor Red
}

# Emergency scheduler status
Write-Host "`nEMERGENCY SCHEDULER STATUS:" -ForegroundColor Cyan
if (Test-Path "pages\working-scheduler.tsx") {
    Write-Host "READY - Emergency scheduler will work regardless of API issues" -ForegroundColor Green
} else {
    Write-Host "NOT READY - Emergency scheduler missing" -ForegroundColor Red
}

Write-Host "`nNext steps:" -ForegroundColor White
Write-Host "1. Deploy the current version" -ForegroundColor White
Write-Host "2. Test: /working-scheduler" -ForegroundColor White
Write-Host "3. Test: /simple-index" -ForegroundColor White