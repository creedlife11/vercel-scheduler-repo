/**
 * Deployment configuration for the scheduler application.
 * Defines environment-specific settings and feature flag defaults.
 */

const deploymentConfig = {
  // Environment detection
  environments: {
    development: {
      name: 'development',
      domain: 'localhost:3000',
      features: {
        enableAuthenticationSystem: false,
        enableRateLimiting: false,
        enableTeamStorage: true,
        enableExperimentalFeatures: true,
        maxWeeksAllowed: 104,
        fairnessThreshold: 0.5
      },
      monitoring: {
        logLevel: 'DEBUG',
        enableMetrics: true,
        enableErrorTracking: false
      },
      security: {
        maxRequestSizeMB: 5.0,
        corsOrigins: ['http://localhost:3000', 'http://127.0.0.1:3000']
      }
    },
    
    preview: {
      name: 'preview',
      domain: '*.vercel.app',
      features: {
        enableAuthenticationSystem: false,
        enableRateLimiting: false,
        enableTeamStorage: true,
        enableExperimentalFeatures: false,
        maxWeeksAllowed: 52,
        fairnessThreshold: 0.7
      },
      monitoring: {
        logLevel: 'INFO',
        enableMetrics: true,
        enableErrorTracking: true
      },
      security: {
        maxRequestSizeMB: 3.0,
        corsOrigins: process.env.CORS_ORIGINS?.split(',') || []
      }
    },
    
    production: {
      name: 'production',
      domain: process.env.PRODUCTION_DOMAIN || 'scheduler.example.com',
      features: {
        enableAuthenticationSystem: false,
        enableRateLimiting: false,
        enableTeamStorage: true,
        enableExperimentalFeatures: false,
        maxWeeksAllowed: 52,
        fairnessThreshold: 0.8
      },
      monitoring: {
        logLevel: 'INFO',
        enableMetrics: process.env.ENABLE_METRICS === 'true',
        enableErrorTracking: true
      },
      security: {
        maxRequestSizeMB: 2.0,
        corsOrigins: process.env.CORS_ORIGINS?.split(',') || []
      }
    }
  },

  // Feature flag rollout configuration
  rolloutConfig: {
    // Gradual rollout features
    enableTeamStorage: {
      development: 100,
      preview: 100,
      production: 50  // 50% rollout in production
    },
    enableArtifactSharing: {
      development: 100,
      preview: 100,
      production: 75  // 75% rollout in production
    },
    enableAdvancedAnalytics: {
      development: 100,
      preview: 25,   // 25% rollout in preview
      production: 0   // Not yet in production
    }
  },

  // Database configuration
  database: {
    development: {
      provider: 'sqlite',
      url: process.env.DATABASE_URL || 'file:./dev.db',
      maxConnections: 5
    },
    preview: {
      provider: 'postgresql',
      url: process.env.DATABASE_URL,
      maxConnections: 10,
      ssl: true
    },
    production: {
      provider: 'postgresql',
      url: process.env.DATABASE_URL,
      maxConnections: 20,
      ssl: true,
      connectionTimeout: 30000
    }
  },

  // Authentication configuration
  auth: {
    development: {
      provider: 'nextauth',
      sessionMaxAge: 3600,  // 1 hour
      allowedDomains: ['localhost']
    },
    preview: {
      provider: 'nextauth',
      sessionMaxAge: 43200, // 12 hours
      allowedDomains: process.env.ALLOWED_DOMAINS?.split(',') || []
    },
    production: {
      provider: 'nextauth',
      sessionMaxAge: 86400, // 24 hours
      allowedDomains: process.env.ALLOWED_DOMAINS?.split(',') || []
    }
  },

  // Rate limiting configuration
  rateLimiting: {
    development: {
      enabled: false
    },
    preview: {
      enabled: true,
      requestsPerHour: 200,
      requestsPerMinute: 20,
      burstLimit: 30
    },
    production: {
      enabled: true,
      requestsPerHour: parseInt(process.env.RATE_LIMIT_HOUR || '100'),
      requestsPerMinute: parseInt(process.env.RATE_LIMIT_MINUTE || '10'),
      burstLimit: parseInt(process.env.RATE_LIMIT_BURST || '20')
    }
  },

  // Monitoring and observability
  monitoring: {
    development: {
      structuredLogging: true,
      performanceMonitoring: true,
      errorTracking: false,
      metricsEndpoint: true
    },
    preview: {
      structuredLogging: true,
      performanceMonitoring: true,
      errorTracking: true,
      metricsEndpoint: true
    },
    production: {
      structuredLogging: true,
      performanceMonitoring: true,
      errorTracking: true,
      metricsEndpoint: process.env.ENABLE_METRICS === 'true'
    }
  }
};

/**
 * Get configuration for the current environment
 */
function getCurrentConfig() {
  const environment = process.env.VERCEL_ENV || 'development';
  
  const config = {
    environment,
    ...deploymentConfig.environments[environment] || deploymentConfig.environments.development,
    database: deploymentConfig.database[environment] || deploymentConfig.database.development,
    auth: deploymentConfig.auth[environment] || deploymentConfig.auth.development,
    rateLimiting: deploymentConfig.rateLimiting[environment] || deploymentConfig.rateLimiting.development,
    monitoring: deploymentConfig.monitoring[environment] || deploymentConfig.monitoring.development
  };

  // Apply rollout percentages
  for (const [feature, rollouts] of Object.entries(deploymentConfig.rolloutConfig)) {
    if (config.features[feature] && typeof config.features[feature] === 'object') {
      config.features[feature].rollout_percentage = rollouts[environment] || 0;
    }
  }

  return config;
}

/**
 * Validate required environment variables for the current environment
 */
function validateEnvironmentVariables() {
  const environment = process.env.VERCEL_ENV || 'development';
  const errors = [];

  // Required for all environments
  const requiredAlways = [];

  // Required for preview and production (only if auth is enabled)
  const requiredNonDev = [];

  // Required for production only
  const requiredProd = [
    'DATABASE_URL'
  ];

  // Check always required
  for (const envVar of requiredAlways) {
    if (!process.env[envVar]) {
      errors.push(`Missing required environment variable: ${envVar}`);
    }
  }

  // Check non-development required
  if (environment !== 'development') {
    for (const envVar of requiredNonDev) {
      if (!process.env[envVar]) {
        errors.push(`Missing required environment variable for ${environment}: ${envVar}`);
      }
    }
  }

  // Check production required
  if (environment === 'production') {
    for (const envVar of requiredProd) {
      if (!process.env[envVar]) {
        errors.push(`Missing required environment variable for production: ${envVar}`);
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Generate Edge Config JSON for Vercel
 */
function generateEdgeConfig() {
  const config = getCurrentConfig();
  
  return {
    // Feature flags
    enableFairnessReporting: {
      enabled: true,
      rollout_percentage: 100,
      description: 'Enable fairness analysis and reporting'
    },
    enableDecisionLogging: {
      enabled: true,
      rollout_percentage: 100,
      description: 'Enable detailed decision logging'
    },
    enableTeamStorage: {
      enabled: config.features.enableTeamStorage,
      rollout_percentage: deploymentConfig.rolloutConfig.enableTeamStorage[config.environment] || 100,
      description: 'Enable team-scoped artifact storage'
    },
    enableArtifactSharing: {
      enabled: config.features.enableArtifactSharing || true,
      rollout_percentage: deploymentConfig.rolloutConfig.enableArtifactSharing[config.environment] || 100,
      description: 'Enable artifact sharing between team members'
    },
    
    // Configuration values
    maxWeeksAllowed: config.features.maxWeeksAllowed,
    fairnessThreshold: config.features.fairnessThreshold,
    
    // Environment info
    environment: config.environment,
    lastUpdated: new Date().toISOString()
  };
}

module.exports = {
  deploymentConfig,
  getCurrentConfig,
  validateEnvironmentVariables,
  generateEdgeConfig
};

// Export for ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports.default = deploymentConfig;
}