#!/usr/bin/env node

/**
 * Deployment verification script
 * Tests critical API endpoints after deployment
 */

const https = require('https');
const http = require('http');

const BASE_URL = process.argv[2] || 'http://localhost:3000';

console.log(`🔍 Verifying deployment at: ${BASE_URL}`);

async function testEndpoint(path, expectedStatus = 200) {
  return new Promise((resolve, reject) => {
    const url = `${BASE_URL}${path}`;
    const client = url.startsWith('https') ? https : http;
    
    console.log(`Testing: ${path}`);
    
    const req = client.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const success = res.statusCode === expectedStatus;
        console.log(`  ${success ? '✅' : '❌'} ${res.statusCode} ${path}`);
        
        if (!success) {
          console.log(`  Response: ${data.substring(0, 200)}...`);
        }
        
        resolve({ success, status: res.statusCode, data });
      });
    });
    
    req.on('error', (err) => {
      console.log(`  ❌ ERROR ${path}: ${err.message}`);
      resolve({ success: false, error: err.message });
    });
    
    req.setTimeout(10000, () => {
      req.destroy();
      console.log(`  ❌ TIMEOUT ${path}`);
      resolve({ success: false, error: 'Timeout' });
    });
  });
}

async function main() {
  console.log('\n🧪 Testing Critical Endpoints...\n');
  
  const tests = [
    // Core pages
    { path: '/', name: 'Home Page' },
    { path: '/scheduler', name: 'Standalone Scheduler' },
    { path: '/auth/signin', name: 'Sign In Page' },
    { path: '/auth-test', name: 'Auth Test Page' },
    
    // API endpoints
    { path: '/api/config/features', name: 'Features API' },
    { path: '/api/auth/session', name: 'NextAuth Session' },
    { path: '/api/generate', name: 'Generate API', expectedStatus: 405 }, // POST only
    
    // Health checks
    { path: '/api/readyz', name: 'Readiness Check' },
  ];
  
  const results = [];
  
  for (const test of tests) {
    const result = await testEndpoint(test.path, test.expectedStatus);
    results.push({ ...test, ...result });
  }
  
  console.log('\n📊 Summary:\n');
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const status = result.success ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} ${result.name}`);
    if (!result.success && result.error) {
      console.log(`     Error: ${result.error}`);
    }
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🚀 Deployment verification PASSED!');
    process.exit(0);
  } else {
    console.log('⚠️  Some tests failed. Check the issues above.');
    process.exit(1);
  }
}

main().catch(console.error);