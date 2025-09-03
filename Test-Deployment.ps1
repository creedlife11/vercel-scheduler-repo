# PowerShell Testing Framework for Team Scheduler
# Tests code structure and validates deployment readiness

param(
    [string]$TestType = "All",
    [switch]$Verbose
)

# Test results tracking
$Global:TestResults = @()
$Global:PassedTests = 0
$Global:FailedTests = 0

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = "",
        [string]$Details = ""
    )
    
    $status = if ($Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($Passed) { "Green" } else { "Red" }
    
    Write-Host "$status $TestName" -ForegroundColor $color
    if ($Message) {
        Write-Host "    $Message" -ForegroundColor Gray
    }
    if ($Details -and $Verbose) {
        Write-Host "    Details: $Details" -ForegroundColor DarkGray
    }
    
    $Global:TestResults += @{
        Name = $TestName
        Passed = $Passed
        Message = $Message
        Details = $Details
    }
    
    if ($Passed) {
        $Global:PassedTests++
    } else {
        $Global:FailedTests++
    }
}

function Test-FileExists {
    param([string]$FilePath, [string]$Description)
    
    $exists = Test-Path $FilePath
    Write-TestResult -TestName "File: $Description" -Passed $exists -Message $FilePath
    return $exists
}

function Test-FileContent {
    param(
        [string]$FilePath,
        [string]$Pattern,
        [string]$Description
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-TestResult -TestName "Content: $Description" -Passed $false -Message "File not found: $FilePath"
        return $false
    }
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction Stop
        $matches = $content -match $Pattern
        Write-TestResult -TestName "Content: $Description" -Passed $matches -Message "Pattern: $Pattern"
        return $matches
    } catch {
        Write-TestResult -TestName "Content: $Description" -Passed $false -Message "Error reading file: $($_.Exception.Message)"
        return $false
    }
}

function Test-JsonSyntax {
    param([string]$FilePath, [string]$Description)
    
    if (-not (Test-Path $FilePath)) {
        Write-TestResult -TestName "JSON: $Description" -Passed $false -Message "File not found"
        return $false
    }
    
    try {
        $content = Get-Content $FilePath -Raw
        $json = ConvertFrom-Json $content -ErrorAction Stop
        Write-TestResult -TestName "JSON: $Description" -Passed $true -Message "Valid JSON syntax"
        return $true
    } catch {
        Write-TestResult -TestName "JSON: $Description" -Passed $false -Message "Invalid JSON: $($_.Exception.Message)"
        return $false
    }
}

function Test-TypeScriptSyntax {
    param([string]$FilePath, [string]$Description)
    
    if (-not (Test-Path $FilePath)) {
        Write-TestResult -TestName "TypeScript: $Description" -Passed $false -Message "File not found"
        return $false
    }
    
    try {
        $content = Get-Content $FilePath -Raw
        
        # Basic syntax checks
        $openBraces = ($content | Select-String -Pattern '\{' -AllMatches).Matches.Count
        $closeBraces = ($content | Select-String -Pattern '\}' -AllMatches).Matches.Count
        $openParens = ($content | Select-String -Pattern '\(' -AllMatches).Matches.Count
        $closeParens = ($content | Select-String -Pattern '\)' -AllMatches).Matches.Count
        
        $braceBalance = $openBraces -eq $closeBraces
        $parenBalance = $openParens -eq $closeParens
        $hasExport = $content -match "export default"
        
        $passed = $braceBalance -and $parenBalance -and $hasExport
        
        $issues = @()
        if (-not $braceBalance) { $issues += "Unbalanced braces ($openBraces open, $closeBraces close)" }
        if (-not $parenBalance) { $issues += "Unbalanced parentheses ($openParens open, $closeParens close)" }
        if (-not $hasExport) { $issues += "Missing export default" }
        
        $message = if ($issues.Count -gt 0) { $issues -join "; " } else { "Basic syntax OK" }
        
        Write-TestResult -TestName "TypeScript: $Description" -Passed $passed -Message $message
        return $passed
    } catch {
        Write-TestResult -TestName "TypeScript: $Description" -Passed $false -Message "Error: $($_.Exception.Message)"
        return $false
    }
}

function Test-ProjectStructure {
    Write-Host "`n🏗️  Testing Project Structure..." -ForegroundColor Cyan
    
    # Required files
    $requiredFiles = @(
        @{ Path = "package.json"; Description = "Package configuration" },
        @{ Path = "pages\_app.tsx"; Description = "Next.js app component" },
        @{ Path = "pages\index.tsx"; Description = "Home page" },
        @{ Path = "pages\working-scheduler.tsx"; Description = "Emergency scheduler" },
        @{ Path = "pages\simple-index.tsx"; Description = "Simple landing page" },
        @{ Path = "pages\api\auth\[...nextauth].ts"; Description = "NextAuth API" },
        @{ Path = "pages\api\config\features.ts"; Description = "Features API" },
        @{ Path = "pages\api\generate.ts"; Description = "Generate API" }
    )
    
    foreach ($file in $requiredFiles) {
        Test-FileExists -FilePath $file.Path -Description $file.Description
    }
    
    # Required directories
    $requiredDirs = @("pages", "pages\api", "pages\auth", "lib", "lib\components")
    foreach ($dir in $requiredDirs) {
        $exists = Test-Path $dir -PathType Container
        Write-TestResult -TestName "Directory: $dir" -Passed $exists
    }
}

function Test-PackageConfiguration {
    Write-Host "`n📦 Testing Package Configuration..." -ForegroundColor Cyan
    
    if (-not (Test-Path "package.json")) {
        Write-TestResult -TestName "Package.json" -Passed $false -Message "File not found"
        return
    }
    
    try {
        $package = Get-Content "package.json" | ConvertFrom-Json
        
        # Check required dependencies
        $requiredDeps = @("next", "next-auth", "react", "react-dom")
        foreach ($dep in $requiredDeps) {
            $exists = $package.dependencies.PSObject.Properties.Name -contains $dep
            Write-TestResult -TestName "Dependency: $dep" -Passed $exists
        }
        
        # Check required scripts
        $requiredScripts = @("dev", "build", "start")
        foreach ($script in $requiredScripts) {
            $exists = $package.scripts.PSObject.Properties.Name -contains $script
            Write-TestResult -TestName "Script: $script" -Passed $exists
        }
        
    } catch {
        Write-TestResult -TestName "Package.json parsing" -Passed $false -Message $_.Exception.Message
    }
}

function Test-TypeScriptFiles {
    Write-Host "`n📝 Testing TypeScript Files..." -ForegroundColor Cyan
    
    $tsFiles = @(
        @{ Path = "pages\working-scheduler.tsx"; Description = "Emergency scheduler component" },
        @{ Path = "pages\simple-index.tsx"; Description = "Simple landing page" },
        @{ Path = "pages\_app.tsx"; Description = "App component" },
        @{ Path = "pages\api\auth\[...nextauth].ts"; Description = "NextAuth configuration" },
        @{ Path = "pages\api\config\features.ts"; Description = "Features API" }
    )
    
    foreach ($file in $tsFiles) {
        if (Test-Path $file.Path) {
            Test-TypeScriptSyntax -FilePath $file.Path -Description $file.Description
        }
    }
}

function Test-ConfigurationFiles {
    Write-Host "`n⚙️  Testing Configuration Files..." -ForegroundColor Cyan
    
    # Test JSON files
    $jsonFiles = @(
        @{ Path = "package.json"; Description = "Package configuration" },
        @{ Path = "vercel.json"; Description = "Vercel configuration" },
        @{ Path = "tsconfig.json"; Description = "TypeScript configuration" }
    )
    
    foreach ($file in $jsonFiles) {
        if (Test-Path $file.Path) {
            Test-JsonSyntax -FilePath $file.Path -Description $file.Description
        }
    }
    
    # Test Next.js config
    if (Test-Path "next.config.js") {
        Test-FileContent -FilePath "next.config.js" -Pattern "module\.exports" -Description "Next.js config export"
    }
}

function Test-EmergencyScheduler {
    Write-Host "`n🚨 Testing Emergency Scheduler..." -ForegroundColor Cyan
    
    $schedulerPath = "pages\working-scheduler.tsx"
    
    if (-not (Test-Path $schedulerPath)) {
        Write-TestResult -TestName "Emergency Scheduler" -Passed $false -Message "File not found"
        return
    }
    
    # Test for required functionality
    $requiredPatterns = @(
        @{ Pattern = "useState"; Description = "React state management" },
        @{ Pattern = "generateSchedule"; Description = "Schedule generation function" },
        @{ Pattern = "downloadCSV"; Description = "CSV download function" },
        @{ Pattern = "export default"; Description = "Component export" },
        @{ Pattern = "engineers\.split"; Description = "Engineer parsing logic" },
        @{ Pattern = "new Date"; Description = "Date handling" }
    )
    
    foreach ($pattern in $requiredPatterns) {
        Test-FileContent -FilePath $schedulerPath -Pattern $pattern.Pattern -Description $pattern.Description
    }
}

function Test-DeploymentReadiness {
    Write-Host "`n🚀 Testing Deployment Readiness..." -ForegroundColor Cyan
    
    # Check for deployment configuration
    $deploymentFiles = @(
        @{ Path = "vercel.json"; Description = "Vercel deployment config" },
        @{ Path = "next.config.js"; Description = "Next.js build config" }
    )
    
    foreach ($file in $deploymentFiles) {
        Test-FileExists -FilePath $file.Path -Description $file.Description
    }
    
    # Check environment template
    $envExists = (Test-Path ".env.local") -or (Test-Path ".env.example")
    Write-TestResult -TestName "Environment configuration" -Passed $envExists -Message "Environment file available"
    
    # Check for build script
    if (Test-Path "package.json") {
        Test-FileContent -FilePath "package.json" -Pattern '"build"' -Description "Build script configured"
    }
}

function Show-TestSummary {
    Write-Host "`n" + "="*60 -ForegroundColor Yellow
    Write-Host "📊 TEST SUMMARY" -ForegroundColor Yellow
    Write-Host "="*60 -ForegroundColor Yellow
    
    $totalTests = $Global:PassedTests + $Global:FailedTests
    Write-Host "Total Tests: $totalTests" -ForegroundColor White
    Write-Host "Passed: $Global:PassedTests" -ForegroundColor Green
    Write-Host "Failed: $Global:FailedTests" -ForegroundColor Red
    
    $successRate = if ($totalTests -gt 0) { [math]::Round(($Global:PassedTests / $totalTests) * 100, 1) } else { 0 }
    Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } else { "Yellow" })
    
    if ($Global:FailedTests -eq 0) {
        Write-Host "`n🎉 ALL TESTS PASSED! Ready for deployment!" -ForegroundColor Green
    } elseif ($successRate -ge 80) {
        Write-Host "`n⚠️  Most tests passed. Review failures but deployment may still work." -ForegroundColor Yellow
    } else {
        Write-Host "`n❌ Multiple test failures. Review issues before deployment." -ForegroundColor Red
    }
    
    # Show failed tests
    if ($Global:FailedTests -gt 0) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        foreach ($result in $Global:TestResults) {
            if (-not $result.Passed) {
                Write-Host "  ❌ $($result.Name): $($result.Message)" -ForegroundColor Red
            }
        }
    }
}

# Main execution
Write-Host "🧪 PowerShell Testing Framework for Team Scheduler" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan

switch ($TestType.ToLower()) {
    "structure" { Test-ProjectStructure }
    "package" { Test-PackageConfiguration }
    "typescript" { Test-TypeScriptFiles }
    "config" { Test-ConfigurationFiles }
    "emergency" { Test-EmergencyScheduler }
    "deployment" { Test-DeploymentReadiness }
    default {
        Test-ProjectStructure
        Test-PackageConfiguration
        Test-TypeScriptFiles
        Test-ConfigurationFiles
        Test-EmergencyScheduler
        Test-DeploymentReadiness
    }
}

Show-TestSummary

# Return exit code based on results
if ($Global:FailedTests -eq 0) {
    exit 0
} else {
    exit 1
}