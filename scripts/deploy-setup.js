#!/usr/bin/env node

/**
 * Deployment setup script for the scheduler application.
 * Validates environment configuration and sets up feature flags.
 */

const { getCurrentConfig, validateEnvironmentVariables, generateEdgeConfig } = require('../deployment.config.js');

async function main() {
  console.log('🚀 Scheduler Deployment Setup');
  console.log('==============================\n');

  // Get current environment
  const environment = process.env.VERCEL_ENV || 'development';
  console.log(`📍 Environment: ${environment}`);

  // Validate environment variables
  console.log('\n🔍 Validating environment variables...');
  const validation = validateEnvironmentVariables();
  
  if (!validation.isValid) {
    console.error('❌ Environment validation failed:');
    validation.errors.forEach(error => console.error(`   - ${error}`));
    process.exit(1);
  }
  
  console.log('✅ Environment variables validated');

  // Get configuration
  const config = getCurrentConfig();
  console.log('\n📋 Current configuration:');
  console.log(`   - Environment: ${config.environment}`);
  console.log(`   - Domain: ${config.domain}`);
  console.log(`   - Auth enabled: ${config.features.enableAuthenticationSystem}`);
  console.log(`   - Rate limiting: ${config.features.enableRateLimiting}`);
  console.log(`   - Max weeks: ${config.features.maxWeeksAllowed}`);
  console.log(`   - Team storage: ${config.features.enableTeamStorage}`);

  // Generate Edge Config
  if (process.env.EDGE_CONFIG && process.env.EDGE_CONFIG_TOKEN) {
    console.log('\n🔧 Updating Vercel Edge Config...');
    
    try {
      const edgeConfig = generateEdgeConfig();
      
      // Update Edge Config via API
      const response = await fetch(
        `https://edge-config.vercel.com/${process.env.EDGE_CONFIG}/items`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${process.env.EDGE_CONFIG_TOKEN}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            items: [
              {
                operation: 'upsert',
                key: 'featureFlags',
                value: edgeConfig
              }
            ]
          })
        }
      );

      if (response.ok) {
        console.log('✅ Edge Config updated successfully');
      } else {
        console.warn(`⚠️  Edge Config update failed: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.warn(`⚠️  Edge Config update error: ${error.message}`);
    }
  } else {
    console.log('\n📝 Edge Config not configured (EDGE_CONFIG and EDGE_CONFIG_TOKEN not set)');
    console.log('   Feature flags will use default values');
  }

  // Database setup check
  if (config.database.url) {
    console.log('\n🗄️  Database configuration:');
    console.log(`   - Provider: ${config.database.provider}`);
    console.log(`   - Max connections: ${config.database.maxConnections}`);
    console.log(`   - SSL: ${config.database.ssl ? 'enabled' : 'disabled'}`);
  } else {
    console.log('\n⚠️  No database URL configured');
  }

  // Security configuration
  console.log('\n🔒 Security configuration:');
  console.log(`   - Max request size: ${config.security.maxRequestSizeMB}MB`);
  console.log(`   - CORS origins: ${config.security.corsOrigins?.length || 0} configured`);
  
  if (config.rateLimiting.enabled) {
    console.log(`   - Rate limiting: ${config.rateLimiting.requestsPerHour}/hour, ${config.rateLimiting.requestsPerMinute}/minute`);
  } else {
    console.log('   - Rate limiting: disabled');
  }

  // Monitoring configuration
  console.log('\n📊 Monitoring configuration:');
  console.log(`   - Log level: ${config.monitoring.logLevel}`);
  console.log(`   - Performance monitoring: ${config.monitoring.performanceMonitoring ? 'enabled' : 'disabled'}`);
  console.log(`   - Error tracking: ${config.monitoring.errorTracking ? 'enabled' : 'disabled'}`);
  console.log(`   - Metrics endpoint: ${config.monitoring.metricsEndpoint ? 'enabled' : 'disabled'}`);

  // Feature flags summary
  console.log('\n🎛️  Feature flags:');
  const features = config.features;
  Object.entries(features).forEach(([key, value]) => {
    if (typeof value === 'boolean') {
      console.log(`   - ${key}: ${value ? 'enabled' : 'disabled'}`);
    } else if (typeof value === 'object' && value.enabled !== undefined) {
      const rollout = value.rollout_percentage || 100;
      console.log(`   - ${key}: ${value.enabled ? 'enabled' : 'disabled'} (${rollout}% rollout)`);
    } else {
      console.log(`   - ${key}: ${value}`);
    }
  });

  console.log('\n✅ Deployment setup complete!');
  
  // Environment-specific next steps
  if (environment === 'development') {
    console.log('\n📝 Development environment notes:');
    console.log('   - Authentication is disabled for easier testing');
    console.log('   - Rate limiting is disabled');
    console.log('   - All experimental features are enabled');
    console.log('   - Run `npm run dev` to start the development server');
  } else if (environment === 'preview') {
    console.log('\n📝 Preview environment notes:');
    console.log('   - This is a staging environment for testing');
    console.log('   - Authentication is enabled');
    console.log('   - Some features may have limited rollout');
    console.log('   - Monitor logs for any issues before promoting to production');
  } else if (environment === 'production') {
    console.log('\n📝 Production environment notes:');
    console.log('   - All security features are enabled');
    console.log('   - Feature rollouts may be gradual');
    console.log('   - Monitor metrics and error rates closely');
    console.log('   - Ensure all required environment variables are set');
  }
}

// Handle command line arguments
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
Scheduler Deployment Setup Script

Usage: node scripts/deploy-setup.js [options]

Options:
  --help, -h     Show this help message
  --config       Show current configuration only
  --validate     Validate environment variables only
  --edge-config  Generate Edge Config JSON only

Environment Variables:
  VERCEL_ENV              Deployment environment (development|preview|production)
  EDGE_CONFIG             Vercel Edge Config ID
  EDGE_CONFIG_TOKEN       Vercel Edge Config token
  DATABASE_URL            Database connection URL
  NEXTAUTH_SECRET         NextAuth.js secret key
  NEXTAUTH_URL            NextAuth.js URL
  ALLOWED_DOMAINS         Comma-separated list of allowed domains
  CORS_ORIGINS            Comma-separated list of CORS origins
  RATE_LIMIT_HOUR         Requests per hour limit
  RATE_LIMIT_MINUTE       Requests per minute limit
  ENABLE_METRICS          Enable metrics endpoint (true/false)
`);
  process.exit(0);
}

if (args.includes('--config')) {
  const config = getCurrentConfig();
  console.log(JSON.stringify(config, null, 2));
  process.exit(0);
}

if (args.includes('--validate')) {
  const validation = validateEnvironmentVariables();
  if (validation.isValid) {
    console.log('✅ Environment variables are valid');
    process.exit(0);
  } else {
    console.error('❌ Environment validation failed:');
    validation.errors.forEach(error => console.error(`   - ${error}`));
    process.exit(1);
  }
}

if (args.includes('--edge-config')) {
  const edgeConfig = generateEdgeConfig();
  console.log(JSON.stringify(edgeConfig, null, 2));
  process.exit(0);
}

// Run main setup
main().catch(error => {
  console.error('❌ Deployment setup failed:', error);
  process.exit(1);
});