#!/usr/bin/env node

/**
 * Pre-ship verification script for the Enhanced Team Scheduler.
 * Validates that all components are ready for production deployment.
 */

const fs = require('fs');
const path = require('path');

console.log('🚀 Enhanced Team Scheduler - Pre-Ship Verification');
console.log('==================================================\n');

let allChecksPass = true;

function checkFile(filePath, description) {
  const exists = fs.existsSync(filePath);
  console.log(`${exists ? '✅' : '❌'} ${description}: ${filePath}`);
  if (!exists) allChecksPass = false;
  return exists;
}

function checkDirectory(dirPath, description) {
  const exists = fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory();
  console.log(`${exists ? '✅' : '❌'} ${description}: ${dirPath}`);
  if (!exists) allChecksPass = false;
  return exists;
}

function checkFileContent(filePath, searchString, description) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const found = content.includes(searchString);
    console.log(`${found ? '✅' : '❌'} ${description}`);
    if (!found) allChecksPass = false;
    return found;
  } catch (error) {
    console.log(`❌ ${description} (file not readable)`);
    allChecksPass = false;
    return false;
  }
}

// 1. Core Application Files
console.log('1. Core Application Files');
console.log('------------------------');
checkFile('api/generate.py', 'Main API endpoint');
checkFile('schedule_core.py', 'Scheduling core logic');
checkFile('export_manager.py', 'Export management');
checkFile('models.py', 'Data models');
checkFile('pages/index.tsx', 'Frontend main page');
checkFile('package.json', 'Node.js dependencies');
checkFile('requirements.txt', 'Python dependencies');
checkFile('vercel.json', 'Vercel configuration');

// 2. Enhanced Features
console.log('\n2. Enhanced Features');
console.log('-------------------');
checkFile('lib/feature_flags.py', 'Feature flag system');
checkFile('lib/config_manager.py', 'Configuration management');
checkFile('lib/hooks/useFeatureFlags.ts', 'Frontend feature flags');
checkFile('pages/api/config/features.ts', 'Feature flag API');
checkFile('lib/components/ArtifactPanel.tsx', 'Enhanced artifact panel');
checkFile('lib/components/LeaveManager.tsx', 'Leave management');
checkFile('lib/components/PresetManager.tsx', 'Preset management');

// 3. Validation and Security
console.log('\n3. Validation and Security');
console.log('-------------------------');
checkFile('lib/validation.ts', 'Frontend validation');
checkFile('lib/auth_middleware.py', 'Authentication middleware');
checkFile('lib/rate_limiter.py', 'Rate limiting');
checkFile('lib/audit_logger.py', 'Audit logging');
checkFile('pages/api/auth/[...nextauth].ts', 'NextAuth configuration');

// 4. Monitoring and Reliability
console.log('\n4. Monitoring and Reliability');
console.log('----------------------------');
checkFile('lib/logging_utils.py', 'Structured logging');
checkFile('lib/performance_monitor.py', 'Performance monitoring');
checkFile('lib/invariant_checker.py', 'Invariant checking');
checkFile('api/healthz.py', 'Health check endpoint');
checkFile('api/readyz.py', 'Readiness check endpoint');
checkFile('api/metrics.py', 'Metrics endpoint');

// 5. Testing Infrastructure
console.log('\n5. Testing Infrastructure');
console.log('------------------------');
checkDirectory('tests/e2e', 'E2E test directory');
checkFile('tests/e2e/scheduler.spec.ts', 'Main E2E tests');
checkFile('test_schedule_invariants.py', 'Python invariant tests');
checkFile('.github/workflows/ci.yml', 'CI/CD pipeline');

// 6. Documentation
console.log('\n6. Documentation');
console.log('---------------');
checkFile('docs/DEPLOYMENT.md', 'Deployment guide');
checkFile('docs/TROUBLESHOOTING.md', 'Troubleshooting guide');
checkFile('docs/OPERATIONS.md', 'Operations runbook');
checkFile('docs/FEATURE_FLAGS.md', 'Feature flag guide');
checkFile('docs/API.md', 'API documentation');
checkFile('README.md', 'Main README');

// 7. Deployment Configuration
console.log('\n7. Deployment Configuration');
console.log('--------------------------');
checkFile('deployment.config.js', 'Deployment configuration');
checkFile('scripts/deploy-setup.js', 'Deployment setup script');
checkFile('.env.development', 'Development environment');
checkFile('.env.production.example', 'Production environment template');

// 8. Content Validation
console.log('\n8. Content Validation');
console.log('--------------------');
checkFileContent('api/generate.py', 'make_enhanced_schedule', 'Enhanced schedule generation integrated');
checkFileContent('pages/index.tsx', 'useFeatureFlags', 'Feature flags integrated in frontend');
checkFileContent('package.json', 'deploy:setup', 'Deployment scripts added');
checkFileContent('vercel.json', 'headers', 'Security headers configured');
checkFileContent('README.md', 'Enhanced Features', 'README updated with new features');

// 9. Feature Flag System
console.log('\n9. Feature Flag System');
console.log('---------------------');
checkFileContent('lib/feature_flags.py', 'FeatureFlagManager', 'Feature flag manager implemented');
checkFileContent('pages/api/config/features.ts', 'enableFairnessReporting', 'Feature flags API configured');
checkFileContent('lib/hooks/useFeatureFlags.ts', 'useFeatureFlags', 'React hook implemented');

// 10. Enhanced Components Integration
console.log('\n10. Enhanced Components Integration');
console.log('----------------------------------');
checkFileContent('api/generate.py', 'is_fairness_reporting_enabled', 'Feature flags integrated in API');
checkFileContent('pages/index.tsx', 'isArtifactPanelEnabled', 'Conditional rendering implemented');
checkFileContent('lib/components/ArtifactPanel.tsx', 'fairness-report', 'Fairness reporting in artifact panel');

// Summary
console.log('\n' + '='.repeat(50));
if (allChecksPass) {
  console.log('🎉 ALL CHECKS PASSED - READY TO SHIP! 🚀');
  console.log('\nNext steps:');
  console.log('1. Initialize git repository: git init');
  console.log('2. Add all files: git add .');
  console.log('3. Commit changes: git commit -m "Enhanced Team Scheduler - Production Ready"');
  console.log('4. Deploy to Vercel: vercel --prod');
  console.log('5. Run post-deployment setup: npm run deploy:setup');
  console.log('\nFor detailed deployment instructions, see docs/DEPLOYMENT.md');
} else {
  console.log('❌ SOME CHECKS FAILED - REVIEW BEFORE SHIPPING');
  console.log('\nPlease address the failed checks above before deployment.');
}

console.log('\n📋 Shipping Summary: SHIPPING_SUMMARY.md');
console.log('📚 Documentation: docs/ directory');
console.log('🔧 Scripts: scripts/ directory');

process.exit(allChecksPass ? 0 : 1);