#!/usr/bin/env node

/**
 * Comprehensive Test Runner
 * Runs all available tests without requiring a development server
 */

const fs = require('fs');
const path = require('path');

// Import our test modules
const { runAllTests: runStaticTests } = require('./test-api-endpoints.js');
const { validateProject } = require('./validate-syntax.js');

// Test configuration validation
async function testConfiguration() {
  console.log('🧪 Testing Configuration...');
  
  const tests = [];
  
  // Check package.json
  try {
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    
    // Check Next.js version
    const nextVersion = packageJson.dependencies?.next;
    if (nextVersion) {
      console.log(`  ✅ Next.js version: ${nextVersion}`);
      tests.push({ name: 'Next.js dependency', passed: true });
    } else {
      console.log(`  ❌ Next.js not found in dependencies`);
      tests.push({ name: 'Next.js dependency', passed: false });
    }
    
    // Check NextAuth version
    const nextAuthVersion = packageJson.dependencies?.['next-auth'];
    if (nextAuthVersion) {
      console.log(`  ✅ NextAuth version: ${nextAuthVersion}`);
      tests.push({ name: 'NextAuth dependency', passed: true });
    } else {
      console.log(`  ❌ NextAuth not found in dependencies`);
      tests.push({ name: 'NextAuth dependency', passed: false });
    }
    
    // Check TypeScript
    const tsVersion = packageJson.devDependencies?.typescript;
    if (tsVersion) {
      console.log(`  ✅ TypeScript version: ${tsVersion}`);
      tests.push({ name: 'TypeScript dependency', passed: true });
    } else {
      console.log(`  ⚠️  TypeScript not found in devDependencies`);
      tests.push({ name: 'TypeScript dependency', passed: false });
    }
    
  } catch (error) {
    console.log(`  ❌ Error reading package.json: ${error.message}`);
    tests.push({ name: 'Package.json', passed: false });
  }
  
  // Check tsconfig.json
  if (fs.existsSync('tsconfig.json')) {
    console.log(`  ✅ TypeScript configuration found`);
    tests.push({ name: 'TypeScript config', passed: true });
  } else {
    console.log(`  ⚠️  tsconfig.json not found`);
    tests.push({ name: 'TypeScript config', passed: false });
  }
  
  // Check Next.js config
  const nextConfigFiles = ['next.config.js', 'next.config.ts', 'next.config.mjs'];
  const hasNextConfig = nextConfigFiles.some(file => fs.existsSync(file));
  
  if (hasNextConfig) {
    console.log(`  ✅ Next.js configuration found`);
    tests.push({ name: 'Next.js config', passed: true });
  } else {
    console.log(`  ℹ️  No Next.js config file (using defaults)`);
    tests.push({ name: 'Next.js config', passed: true }); // Optional
  }
  
  return tests.every(t => t.passed);
}

// Test API route structure
async function testAPIRoutes() {
  console.log('🧪 Testing API Routes...');
  
  const apiRoutes = [
    { path: 'pages/api/generate.ts', name: 'Schedule Generation API' },
    { path: 'pages/api/config/features.ts', name: 'Features Configuration API' },
    { path: 'pages/api/auth/[...nextauth].ts', name: 'NextAuth API' },
    { path: 'pages/api/readyz.py', name: 'Health Check API' }
  ];
  
  let allGood = true;
  
  for (const route of apiRoutes) {
    if (fs.existsSync(route.path)) {
      console.log(`  ✅ ${route.name}`);
      
      // Basic content validation
      const content = fs.readFileSync(route.path, 'utf8');
      
      if (route.path.endsWith('.ts') || route.path.endsWith('.js')) {
        if (content.includes('export default')) {
          console.log(`    ✅ Has default export`);
        } else {
          console.log(`    ⚠️  Missing default export`);
        }
        
        if (content.includes('req') && content.includes('res')) {
          console.log(`    ✅ Has request/response handling`);
        } else {
          console.log(`    ⚠️  Missing req/res parameters`);
        }
      }
      
    } else {
      console.log(`  ❌ ${route.name} - file not found`);
      allGood = false;
    }
  }
  
  return allGood;
}

// Test page components
async function testPageComponents() {
  console.log('🧪 Testing Page Components...');
  
  const pages = [
    { path: 'pages/index.tsx', name: 'Home Page' },
    { path: 'pages/scheduler.tsx', name: 'Standalone Scheduler' },
    { path: 'pages/auth-test.tsx', name: 'Auth Test Page' },
    { path: 'pages/auth/signin.tsx', name: 'Sign In Page' },
    { path: 'pages/auth/error.tsx', name: 'Auth Error Page' },
    { path: 'pages/_app.tsx', name: 'App Component' }
  ];
  
  let allGood = true;
  
  for (const page of pages) {
    if (fs.existsSync(page.path)) {
      console.log(`  ✅ ${page.name}`);
      
      const content = fs.readFileSync(page.path, 'utf8');
      
      // Check for React component structure
      if (content.includes('export default')) {
        console.log(`    ✅ Has default export`);
      } else {
        console.log(`    ⚠️  Missing default export`);
        allGood = false;
      }
      
      // Check for JSX/TSX
      if (content.includes('return') && (content.includes('<') || content.includes('jsx'))) {
        console.log(`    ✅ Contains JSX/TSX`);
      } else if (!page.path.includes('_app')) { // _app might not have JSX
        console.log(`    ⚠️  No JSX found`);
      }
      
    } else {
      console.log(`  ❌ ${page.name} - file not found`);
      allGood = false;
    }
  }
  
  return allGood;
}

// Test authentication setup
async function testAuthSetup() {
  console.log('🧪 Testing Authentication Setup...');
  
  let allGood = true;
  
  // Check NextAuth configuration
  const authConfigPath = 'pages/api/auth/[...nextauth].ts';
  if (fs.existsSync(authConfigPath)) {
    console.log(`  ✅ NextAuth configuration exists`);
    
    const content = fs.readFileSync(authConfigPath, 'utf8');
    
    const checks = [
      { name: 'Credentials provider', pattern: /CredentialsProvider/ },
      { name: 'Demo users', pattern: /demo@example\.com/ },
      { name: 'Auth options export', pattern: /export.*authOptions/ },
      { name: 'JWT strategy', pattern: /jwt/ },
      { name: 'Session callbacks', pattern: /session.*callback/i }
    ];
    
    for (const check of checks) {
      if (check.pattern.test(content)) {
        console.log(`    ✅ ${check.name}`);
      } else {
        console.log(`    ⚠️  ${check.name} not found`);
      }
    }
    
  } else {
    console.log(`  ❌ NextAuth configuration missing`);
    allGood = false;
  }
  
  // Check AuthWrapper component
  const authWrapperPath = 'lib/components/AuthWrapper.tsx';
  if (fs.existsSync(authWrapperPath)) {
    console.log(`  ✅ AuthWrapper component exists`);
    
    const content = fs.readFileSync(authWrapperPath, 'utf8');
    
    if (content.includes('useSession')) {
      console.log(`    ✅ Uses NextAuth session`);
    } else {
      console.log(`    ⚠️  Missing useSession hook`);
    }
    
    if (content.includes('bypass')) {
      console.log(`    ✅ Has bypass functionality`);
    } else {
      console.log(`    ⚠️  Missing bypass functionality`);
    }
    
  } else {
    console.log(`  ❌ AuthWrapper component missing`);
    allGood = false;
  }
  
  return allGood;
}

// Test deployment readiness
async function testDeploymentReadiness() {
  console.log('🧪 Testing Deployment Readiness...');
  
  const checks = [
    {
      name: 'Build script',
      test: () => {
        const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        return pkg.scripts && pkg.scripts.build;
      }
    },
    {
      name: 'Start script',
      test: () => {
        const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        return pkg.scripts && pkg.scripts.start;
      }
    },
    {
      name: 'Environment template',
      test: () => fs.existsSync('.env.local') || fs.existsSync('.env.example')
    },
    {
      name: 'Vercel configuration',
      test: () => fs.existsSync('vercel.json') || true // Optional
    },
    {
      name: 'README documentation',
      test: () => fs.existsSync('README.md')
    }
  ];
  
  let allGood = true;
  
  for (const check of checks) {
    try {
      if (check.test()) {
        console.log(`  ✅ ${check.name}`);
      } else {
        console.log(`  ⚠️  ${check.name} missing`);
        if (check.name !== 'Vercel configuration') { // Vercel config is optional
          allGood = false;
        }
      }
    } catch (error) {
      console.log(`  ❌ ${check.name} - error: ${error.message}`);
      allGood = false;
    }
  }
  
  return allGood;
}

// Main test runner
async function runComprehensiveTests() {
  console.log('🚀 Starting Comprehensive Test Suite\n');
  console.log('=' .repeat(60));
  
  const testSuites = [
    { name: 'Configuration', fn: testConfiguration },
    { name: 'API Routes', fn: testAPIRoutes },
    { name: 'Page Components', fn: testPageComponents },
    { name: 'Authentication Setup', fn: testAuthSetup },
    { name: 'Deployment Readiness', fn: testDeploymentReadiness },
    { name: 'Syntax Validation', fn: validateProject },
    { name: 'Static Analysis', fn: runStaticTests }
  ];
  
  const results = [];
  
  for (const suite of testSuites) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Running: ${suite.name}`);
    console.log(`${'='.repeat(60)}`);
    
    try {
      const result = await suite.fn();
      results.push({ name: suite.name, passed: result });
      
      if (result) {
        console.log(`\n✅ ${suite.name} - PASSED`);
      } else {
        console.log(`\n❌ ${suite.name} - FAILED`);
      }
      
    } catch (error) {
      console.log(`\n❌ ${suite.name} - ERROR: ${error.message}`);
      results.push({ name: suite.name, passed: false });
    }
  }
  
  // Final summary
  console.log(`\n${'='.repeat(60)}`);
  console.log('🎯 FINAL TEST RESULTS');
  console.log(`${'='.repeat(60)}`);
  
  let passed = 0;
  for (const result of results) {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} ${result.name}`);
    if (result.passed) passed++;
  }
  
  console.log(`\n📊 Overall: ${passed}/${results.length} test suites passed`);
  
  if (passed === results.length) {
    console.log('\n🚀 ALL TESTS PASSED! 🎉');
    console.log('Your application is ready for deployment!');
    return true;
  } else {
    console.log('\n⚠️  Some tests failed. Please review the issues above.');
    console.log('The application may still work, but fixing these issues will improve reliability.');
    return false;
  }
}

// Run tests if called directly
if (require.main === module) {
  runComprehensiveTests()
    .then(success => {
      console.log(`\nTest run completed. Exit code: ${success ? 0 : 1}`);
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('\nTest runner crashed:', error);
      process.exit(1);
    });
}

module.exports = { runComprehensiveTests };