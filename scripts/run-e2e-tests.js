#!/usr/bin/env node

/**
 * E2E Test Runner Script
 * 
 * This script provides a comprehensive way to run the E2E test suite
 * with proper setup, validation, and reporting.
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:3000',
  headless: process.env.CI === 'true',
  browsers: ['chromium', 'firefox', 'webkit'],
  timeout: 30000,
  retries: process.env.CI === 'true' ? 2 : 0
};

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkPrerequisites() {
  log('🔍 Checking prerequisites...', 'blue');
  
  // Check if package.json exists
  if (!fs.existsSync('package.json')) {
    log('❌ package.json not found. Run this script from the project root.', 'red');
    process.exit(1);
  }
  
  // Check if Playwright is installed
  try {
    execSync('npx playwright --version', { stdio: 'pipe' });
    log('✅ Playwright is installed', 'green');
  } catch (error) {
    log('❌ Playwright not found. Installing...', 'yellow');
    try {
      execSync('npm install @playwright/test', { stdio: 'inherit' });
      log('✅ Playwright installed successfully', 'green');
    } catch (installError) {
      log('❌ Failed to install Playwright', 'red');
      process.exit(1);
    }
  }
  
  // Check if browsers are installed
  try {
    execSync('npx playwright install --dry-run', { stdio: 'pipe' });
    log('✅ Playwright browsers are installed', 'green');
  } catch (error) {
    log('⚠️  Installing Playwright browsers...', 'yellow');
    try {
      execSync('npx playwright install', { stdio: 'inherit' });
      log('✅ Browsers installed successfully', 'green');
    } catch (installError) {
      log('❌ Failed to install browsers', 'red');
      process.exit(1);
    }
  }
  
  // Check if test files exist
  const testFiles = [
    'tests/e2e/scheduler.spec.ts',
    'tests/e2e/invariant-validation.spec.ts',
    'tests/e2e/visual-regression.spec.ts',
    'tests/e2e/download-validation.spec.ts'
  ];
  
  for (const testFile of testFiles) {
    if (!fs.existsSync(testFile)) {
      log(`❌ Test file not found: ${testFile}`, 'red');
      process.exit(1);
    }
  }
  
  log('✅ All test files found', 'green');
}

function checkServerHealth() {
  log('🏥 Checking server health...', 'blue');
  
  return new Promise((resolve, reject) => {
    const http = require('http');
    const url = new URL(CONFIG.baseUrl);
    
    const req = http.get({
      hostname: url.hostname,
      port: url.port || 80,
      path: '/',
      timeout: 5000
    }, (res) => {
      if (res.statusCode === 200) {
        log('✅ Server is responding', 'green');
        resolve(true);
      } else {
        log(`⚠️  Server responded with status ${res.statusCode}`, 'yellow');
        resolve(false);
      }
    });
    
    req.on('error', (error) => {
      log(`❌ Server health check failed: ${error.message}`, 'red');
      resolve(false);
    });
    
    req.on('timeout', () => {
      log('❌ Server health check timed out', 'red');
      req.destroy();
      resolve(false);
    });
  });
}

async function startDevServer() {
  log('🚀 Starting development server...', 'blue');
  
  return new Promise((resolve, reject) => {
    const server = spawn('npm', ['run', 'dev'], {
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true
    });
    
    let serverReady = false;
    
    server.stdout.on('data', (data) => {
      const output = data.toString();
      if (output.includes('Ready on') || output.includes('Local:')) {
        if (!serverReady) {
          serverReady = true;
          log('✅ Development server started', 'green');
          resolve(server);
        }
      }
    });
    
    server.stderr.on('data', (data) => {
      const error = data.toString();
      if (error.includes('EADDRINUSE')) {
        log('⚠️  Port already in use, assuming server is running', 'yellow');
        resolve(null);
      }
    });
    
    server.on('error', (error) => {
      log(`❌ Failed to start server: ${error.message}`, 'red');
      reject(error);
    });
    
    // Timeout after 30 seconds
    setTimeout(() => {
      if (!serverReady) {
        log('❌ Server startup timed out', 'red');
        server.kill();
        reject(new Error('Server startup timeout'));
      }
    }, 30000);
  });
}

function runTests(options = {}) {
  log('🧪 Running E2E tests...', 'blue');
  
  const args = ['playwright', 'test'];
  
  // Add configuration options
  if (options.headed) {
    args.push('--headed');
  }
  
  if (options.debug) {
    args.push('--debug');
  }
  
  if (options.project) {
    args.push('--project', options.project);
  }
  
  if (options.grep) {
    args.push('--grep', options.grep);
  }
  
  if (options.reporter) {
    args.push('--reporter', options.reporter);
  } else {
    args.push('--reporter', 'html');
  }
  
  // Add specific test file if provided
  if (options.testFile) {
    args.push(options.testFile);
  }
  
  try {
    execSync(`npx ${args.join(' ')}`, { 
      stdio: 'inherit',
      env: {
        ...process.env,
        BASE_URL: CONFIG.baseUrl,
        CI: process.env.CI || 'false'
      }
    });
    
    log('✅ All tests passed!', 'green');
    return true;
  } catch (error) {
    log('❌ Some tests failed', 'red');
    log('📊 Check the HTML report for details: npx playwright show-report', 'cyan');
    return false;
  }
}

function generateTestReport() {
  log('📊 Generating test report...', 'blue');
  
  try {
    execSync('npx playwright show-report', { stdio: 'inherit' });
  } catch (error) {
    log('⚠️  Could not open test report automatically', 'yellow');
    log('💡 Run "npx playwright show-report" to view the report', 'cyan');
  }
}

async function main() {
  const args = process.argv.slice(2);
  const options = {};
  
  // Parse command line arguments
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    switch (arg) {
      case '--headed':
        options.headed = true;
        break;
      case '--debug':
        options.debug = true;
        break;
      case '--project':
        options.project = args[++i];
        break;
      case '--grep':
        options.grep = args[++i];
        break;
      case '--reporter':
        options.reporter = args[++i];
        break;
      case '--help':
        console.log(`
E2E Test Runner

Usage: node scripts/run-e2e-tests.js [options] [test-file]

Options:
  --headed          Run tests in headed mode (show browser)
  --debug           Run tests in debug mode
  --project <name>  Run tests for specific browser (chromium, firefox, webkit)
  --grep <pattern>  Run tests matching pattern
  --reporter <type> Use specific reporter (html, json, junit)
  --help            Show this help message

Examples:
  node scripts/run-e2e-tests.js                                    # Run all tests
  node scripts/run-e2e-tests.js --headed                          # Run with browser UI
  node scripts/run-e2e-tests.js --project chromium                # Run only in Chrome
  node scripts/run-e2e-tests.js --grep "should validate"          # Run validation tests
  node scripts/run-e2e-tests.js tests/e2e/scheduler.spec.ts       # Run specific file
        `);
        process.exit(0);
      default:
        if (arg.endsWith('.spec.ts')) {
          options.testFile = arg;
        }
        break;
    }
  }
  
  try {
    log('🎭 E2E Test Runner Starting...', 'magenta');
    
    // Step 1: Check prerequisites
    checkPrerequisites();
    
    // Step 2: Check if server is running
    const serverHealthy = await checkServerHealth();
    let devServer = null;
    
    if (!serverHealthy) {
      // Step 3: Start dev server if needed
      devServer = await startDevServer();
      
      // Wait a bit for server to fully start
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Verify server is now healthy
      const serverNowHealthy = await checkServerHealth();
      if (!serverNowHealthy) {
        log('❌ Could not start or connect to development server', 'red');
        process.exit(1);
      }
    }
    
    // Step 4: Run tests
    const success = runTests(options);
    
    // Step 5: Cleanup
    if (devServer) {
      log('🛑 Stopping development server...', 'blue');
      devServer.kill();
    }
    
    // Step 6: Show results
    if (success) {
      log('🎉 All tests completed successfully!', 'green');
      process.exit(0);
    } else {
      log('💥 Some tests failed. Check the report for details.', 'red');
      process.exit(1);
    }
    
  } catch (error) {
    log(`💥 Test runner failed: ${error.message}`, 'red');
    process.exit(1);
  }
}

// Handle process termination
process.on('SIGINT', () => {
  log('\n🛑 Test runner interrupted', 'yellow');
  process.exit(1);
});

process.on('SIGTERM', () => {
  log('\n🛑 Test runner terminated', 'yellow');
  process.exit(1);
});

// Run the main function
if (require.main === module) {
  main().catch(error => {
    log(`💥 Unexpected error: ${error.message}`, 'red');
    process.exit(1);
  });
}

module.exports = {
  checkPrerequisites,
  checkServerHealth,
  runTests,
  generateTestReport
};