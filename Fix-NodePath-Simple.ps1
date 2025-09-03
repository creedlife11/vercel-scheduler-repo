# Fix Node.js PATH Issue - Simple version

Write-Host "Fixing Node.js PATH Configuration..." -ForegroundColor Yellow

# Check if Node.js is already in PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$nodePath = "C:\Program Files\nodejs"

if ($currentPath -notlike "*$nodePath*") {
    Write-Host "Adding Node.js to user PATH..." -ForegroundColor Green
    
    # Add to user PATH permanently
    $newPath = $currentPath + ";" + $nodePath
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    
    Write-Host "Node.js added to PATH permanently!" -ForegroundColor Green
    Write-Host "You may need to restart your terminal for changes to take effect." -ForegroundColor Yellow
} else {
    Write-Host "Node.js is already in PATH" -ForegroundColor Green
}

# Test current session
Write-Host "Testing Node.js in current session..." -ForegroundColor Cyan
try {
    $nodeVersion = node --version
    $npmVersion = npm --version
    Write-Host "Node.js: $nodeVersion" -ForegroundColor Green
    Write-Host "npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "Node.js not working in current session" -ForegroundColor Red
    Write-Host "Try restarting your terminal" -ForegroundColor Yellow
}

Write-Host "Ready to deploy!" -ForegroundColor Green