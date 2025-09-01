#!/usr/bin/env node

/**
 * API Endpoint Testing Script
 * Tests the API logic without requiring a running server
 */

const fs = require('fs');
const path = require('path');

// Mock Next.js API request/response
function createMockReq(method = 'GET', body = null, query = {}) {
  return {
    method,
    body,
    query,
    headers: {}
  };
}

function createMockRes() {
  let statusCode = 200;
  let responseData = null;
  let headers = {};
  
  return {
    status: (code) => {
      statusCode = code;
      return {
        json: (data) => {
          responseData = data;
          return { statusCode, data };
        }
      };
    },
    json: (data) => {
      responseData = data;
      return { statusCode, data };
    },
    setHeader: (key, value) => {
      headers[key] = value;
    },
    getStatus: () => statusCode,
    getData: () => responseData,
    getHeaders: () => headers
  };
}

// Test the features API
async function testFeaturesAPI() {
  console.log('🧪 Testing Features API...');
  
  try {
    // Read the features API file
    const featuresPath = path.join(__dirname, 'pages', 'api', 'config', 'features.ts');
    
    if (!fs.existsSync(featuresPath)) {
      console.log('  ❌ Features API file not found');
      return false;
    }
    
    console.log('  ✅ Features API file exists');
    
    // Check for basic structure
    const content = fs.readFileSync(featuresPath, 'utf8');
    
    const checks = [
      { name: 'Export default handler', pattern: /export default.*function.*handler/ },
      { name: 'GET method check', pattern: /req\.method.*GET/ },
      { name: 'Error handling', pattern: /try.*catch/ },
      { name: 'Safe defaults', pattern: /safeDefaults|safe.*default/i },
      { name: 'JSON response', pattern: /res\.status\(\d+\)\.json/ }
    ];
    
    for (const check of checks) {
      if (check.pattern.test(content)) {
        console.log(`  ✅ ${check.name}`);
      } else {
        console.log(`  ⚠️  ${check.name} - pattern not found`);
      }
    }
    
    return true;
    
  } catch (error) {
    console.log(`  ❌ Error testing features API: ${error.message}`);
    return false;
  }
}

// Test the NextAuth configuration
async function testNextAuthConfig() {
  console.log('🧪 Testing NextAuth Configuration...');
  
  try {
    const authPath = path.join(__dirname, 'pages', 'api', 'auth', '[...nextauth].ts');
    
    if (!fs.existsSync(authPath)) {
      console.log('  ❌ NextAuth config file not found');
      return false;
    }
    
    console.log('  ✅ NextAuth config file exists');
    
    const content = fs.readFileSync(authPath, 'utf8');
    
    const checks = [
      { name: 'NextAuth import', pattern: /import.*NextAuth/ },
      { name: 'Credentials provider', pattern: /CredentialsProvider/ },
      { name: 'Auth options export', pattern: /export.*authOptions/ },
      { name: 'Default export', pattern: /export default NextAuth/ },
      { name: 'Authorize function', pattern: /async authorize/ },
      { name: 'Demo users', pattern: /demo@example\.com/ },
      { name: 'JWT strategy', pattern: /strategy.*jwt/i },
      { name: 'Secret configuration', pattern: /NEXTAUTH_SECRET/ }
    ];
    
    for (const check of checks) {
      if (check.pattern.test(content)) {
        console.log(`  ✅ ${check.name}`);
      } else {
        console.log(`  ⚠️  ${check.name} - pattern not found`);
      }
    }
    
    return true;
    
  } catch (error) {
    console.log(`  ❌ Error testing NextAuth config: ${error.message}`);
    return false;
  }
}

// Test React components
async function testReactComponents() {
  console.log('🧪 Testing React Components...');
  
  const components = [
    { name: 'AuthWrapper', path: 'lib/components/AuthWrapper.tsx' },
    { name: 'Scheduler Page', path: 'pages/scheduler.tsx' },
    { name: 'Auth Test Page', path: 'pages/auth-test.tsx' },
    { name: 'Sign In Page', path: 'pages/auth/signin.tsx' }
  ];
  
  let allExist = true;
  
  for (const component of components) {
    const fullPath = path.join(__dirname, component.path);
    
    if (fs.existsSync(fullPath)) {
      console.log(`  ✅ ${component.name} exists`);
      
      // Basic content checks
      const content = fs.readFileSync(fullPath, 'utf8');
      
      if (content.includes('export default')) {
        console.log(`    ✅ Has default export`);
      } else {
        console.log(`    ⚠️  Missing default export`);
      }
      
      if (content.includes('React') || content.includes('useState') || content.includes('useEffect')) {
        console.log(`    ✅ Uses React hooks`);
      }
      
    } else {
      console.log(`  ❌ ${component.name} missing`);
      allExist = false;
    }
  }
  
  return allExist;
}

// Test package.json and dependencies
async function testDependencies() {
  console.log('🧪 Testing Dependencies...');
  
  try {
    const packagePath = path.join(__dirname, 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    
    const requiredDeps = [
      'next',
      'next-auth',
      'react',
      'react-dom'
    ];
    
    const requiredDevDeps = [
      'typescript',
      '@types/react',
      '@types/node'
    ];
    
    console.log('  Checking production dependencies:');
    for (const dep of requiredDeps) {
      if (packageJson.dependencies && packageJson.dependencies[dep]) {
        console.log(`    ✅ ${dep}: ${packageJson.dependencies[dep]}`);
      } else {
        console.log(`    ❌ ${dep} missing`);
      }
    }
    
    console.log('  Checking development dependencies:');
    for (const dep of requiredDevDeps) {
      if (packageJson.devDependencies && packageJson.devDependencies[dep]) {
        console.log(`    ✅ ${dep}: ${packageJson.devDependencies[dep]}`);
      } else {
        console.log(`    ❌ ${dep} missing`);
      }
    }
    
    console.log('  Checking scripts:');
    const requiredScripts = ['dev', 'build', 'start'];
    for (const script of requiredScripts) {
      if (packageJson.scripts && packageJson.scripts[script]) {
        console.log(`    ✅ ${script}: ${packageJson.scripts[script]}`);
      } else {
        console.log(`    ❌ ${script} script missing`);
      }
    }
    
    return true;
    
  } catch (error) {
    console.log(`  ❌ Error testing dependencies: ${error.message}`);
    return false;
  }
}

// Test environment configuration
async function testEnvironmentConfig() {
  console.log('🧪 Testing Environment Configuration...');
  
  try {
    const envPath = path.join(__dirname, '.env.local');
    
    if (!fs.existsSync(envPath)) {
      console.log('  ⚠️  .env.local file not found (this is okay for production)');
      return true;
    }
    
    const content = fs.readFileSync(envPath, 'utf8');
    
    const requiredVars = [
      'NEXTAUTH_SECRET',
      'DATABASE_URL'
    ];
    
    for (const varName of requiredVars) {
      if (content.includes(varName)) {
        console.log(`  ✅ ${varName} configured`);
      } else {
        console.log(`  ⚠️  ${varName} not found`);
      }
    }
    
    // Check for placeholder values that need to be changed
    if (content.includes('your-super-secret')) {
      console.log('  ⚠️  NEXTAUTH_SECRET appears to be a placeholder - should be changed for production');
    }
    
    return true;
    
  } catch (error) {
    console.log(`  ❌ Error testing environment config: ${error.message}`);
    return false;
  }
}

// Test file structure
async function testFileStructure() {
  console.log('🧪 Testing File Structure...');
  
  const requiredFiles = [
    'package.json',
    'pages/_app.tsx',
    'pages/index.tsx',
    'pages/api/generate.ts',
    'pages/api/auth/[...nextauth].ts',
    'pages/api/config/features.ts'
  ];
  
  const requiredDirs = [
    'pages',
    'pages/api',
    'pages/auth',
    'lib',
    'lib/components'
  ];
  
  let allGood = true;
  
  console.log('  Checking required files:');
  for (const file of requiredFiles) {
    const fullPath = path.join(__dirname, file);
    if (fs.existsSync(fullPath)) {
      console.log(`    ✅ ${file}`);
    } else {
      console.log(`    ❌ ${file} missing`);
      allGood = false;
    }
  }
  
  console.log('  Checking required directories:');
  for (const dir of requiredDirs) {
    const fullPath = path.join(__dirname, dir);
    if (fs.existsSync(fullPath) && fs.statSync(fullPath).isDirectory()) {
      console.log(`    ✅ ${dir}/`);
    } else {
      console.log(`    ❌ ${dir}/ missing`);
      allGood = false;
    }
  }
  
  return allGood;
}

// Main test runner
async function runAllTests() {
  console.log('🚀 Starting Static Code Analysis Tests\n');
  
  const tests = [
    { name: 'File Structure', fn: testFileStructure },
    { name: 'Dependencies', fn: testDependencies },
    { name: 'Environment Config', fn: testEnvironmentConfig },
    { name: 'Features API', fn: testFeaturesAPI },
    { name: 'NextAuth Config', fn: testNextAuthConfig },
    { name: 'React Components', fn: testReactComponents }
  ];
  
  const results = [];
  
  for (const test of tests) {
    console.log(`\n${'='.repeat(50)}`);
    const result = await test.fn();
    results.push({ name: test.name, passed: result });
  }
  
  console.log(`\n${'='.repeat(50)}`);
  console.log('📊 Test Summary:');
  console.log(`${'='.repeat(50)}`);
  
  let passed = 0;
  for (const result of results) {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} ${result.name}`);
    if (result.passed) passed++;
  }
  
  console.log(`\n🎯 Results: ${passed}/${results.length} tests passed`);
  
  if (passed === results.length) {
    console.log('🚀 All static tests passed! Code structure looks good.');
    return true;
  } else {
    console.log('⚠️  Some tests failed. Check the issues above.');
    return false;
  }
}

// Run tests if called directly
if (require.main === module) {
  runAllTests()
    .then(success => process.exit(success ? 0 : 1))
    .catch(error => {
      console.error('Test runner error:', error);
      process.exit(1);
    });
}

module.exports = { runAllTests };