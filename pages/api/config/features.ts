/**
 * API endpoint to expose feature flags and configuration to the frontend.
 * Provides client-side access to feature toggles for conditional rendering.
 */

import { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '../auth/[...nextauth]';

interface FeatureConfig {
  [key: string]: {
    enabled: boolean;
    rollout_percentage?: number;
    description?: string;
  } | boolean | number | string;
}

interface ApiResponse {
  features: FeatureConfig;
  environment: string;
  timestamp: string;
}

interface ErrorResponse {
  error: string;
  message: string;
  timestamp: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ApiResponse | ErrorResponse>
) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({
      error: 'Method Not Allowed',
      message: 'Only GET requests are allowed',
      timestamp: new Date().toISOString()
    });
  }

  try {
    // Get user session for user-specific feature flags
    const session = await getServerSession(req, res, authOptions);
    const userId = session?.user?.id || null;
    // const userGroups = session?.user?.groups || [];

    // Get environment
    const environment = process.env.VERCEL_ENV || 'development';

    // Define feature flags configuration
    const features: FeatureConfig = {
      // Core enhanced features
      enableFairnessReporting: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable fairness analysis and reporting in schedule generation'
      },
      enableDecisionLogging: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable detailed decision logging during schedule generation'
      },
      enableAdvancedValidation: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable enhanced input validation with name hygiene'
      },
      enablePerformanceMonitoring: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable performance monitoring and metrics collection'
      },
      enableInvariantChecking: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable scheduling invariant validation'
      },

      // UI features
      enableArtifactPanel: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable enhanced artifact panel with multiple format tabs'
      },
      enableLeaveManagement: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable leave management with CSV/XLSX import'
      },
      enablePresetManager: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable preset configuration system'
      },

      // Security and auth features (environment-dependent)
      enableAuthenticationSystem: {
        enabled: environment !== 'development',
        rollout_percentage: 100,
        description: 'Enable authentication and authorization system'
      },
      enableRateLimiting: {
        enabled: environment !== 'development',
        rollout_percentage: 100,
        description: 'Enable request rate limiting and security controls'
      },

      // Gradual rollout features
      enableTeamStorage: {
        enabled: true,
        rollout_percentage: environment === 'production' ? 50 : 100,
        description: 'Enable team-scoped artifact storage (gradual rollout in production)'
      },
      enableArtifactSharing: {
        enabled: true,
        rollout_percentage: environment === 'production' ? 75 : 100,
        description: 'Enable artifact sharing between team members'
      },

      // Experimental features (development only)
      enableExperimentalFeatures: {
        enabled: environment === 'development',
        rollout_percentage: 100,
        description: 'Enable experimental features for testing'
      },
      enableAdvancedAnalytics: {
        enabled: false,
        rollout_percentage: 0,
        description: 'Enable advanced analytics and insights (coming soon)'
      },

      // Configuration values
      maxWeeksAllowed: parseInt(process.env.MAX_WEEKS_ALLOWED || '52'),
      fairnessThreshold: parseFloat(process.env.FAIRNESS_THRESHOLD || '0.8'),
      maxRequestSizeMB: parseFloat(process.env.MAX_REQUEST_SIZE_MB || '2.0'),
      
      // UI configuration
      enableDarkMode: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable dark mode toggle'
      },
      enableKeyboardShortcuts: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable keyboard shortcuts for power users'
      },
      enableTooltips: {
        enabled: true,
        rollout_percentage: 100,
        description: 'Enable helpful tooltips throughout the interface'
      }
    };

    // Apply user-specific rollout logic
    const processedFeatures: FeatureConfig = {};
    
    for (const [key, config] of Object.entries(features)) {
      if (typeof config === 'object' && config !== null && 'enabled' in config) {
        const rolloutPercentage = config.rollout_percentage || 100;
        
        // Determine if user is in rollout
        let isInRollout = true;
        if (rolloutPercentage < 100) {
          // Use deterministic rollout based on user ID or feature name
          const rolloutKey = userId || key;
          const rolloutHash = Math.abs(hashCode(rolloutKey)) % 100;
          isInRollout = rolloutHash < rolloutPercentage;
        }
        
        processedFeatures[key] = {
          ...config,
          enabled: config.enabled && isInRollout
        };
      } else {
        // Simple value, pass through
        processedFeatures[key] = config;
      }
    }

    // Add environment-specific overrides from Edge Config if available
    if (process.env.EDGE_CONFIG && process.env.EDGE_CONFIG_TOKEN) {
      try {
        const edgeConfigResponse = await fetch(
          `https://edge-config.vercel.com/${process.env.EDGE_CONFIG}/items`,
          {
            headers: {
              'Authorization': `Bearer ${process.env.EDGE_CONFIG_TOKEN}`,
              'Content-Type': 'application/json'
            }
          }
        );
        
        if (edgeConfigResponse.ok) {
          const edgeConfig = await edgeConfigResponse.json();
          
          // Override with Edge Config values
          for (const [key, value] of Object.entries(edgeConfig)) {
            if (key in processedFeatures) {
              processedFeatures[key] = value as any;
            }
          }
        }
      } catch (error) {
        // Log error but don't fail the request
        console.warn('Failed to fetch Edge Config:', error);
      }
    }

    const response: ApiResponse = {
      features: processedFeatures,
      environment,
      timestamp: new Date().toISOString()
    };

    // Set cache headers based on environment
    const cacheMaxAge = environment === 'production' ? 300 : 60; // 5 minutes in prod, 1 minute in dev
    res.setHeader('Cache-Control', `public, max-age=${cacheMaxAge}, s-maxage=${cacheMaxAge}`);
    res.setHeader('Vary', 'Authorization');

    res.status(200).json(response);

  } catch (error) {
    console.error('Feature config API error:', error);
    
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to load feature configuration',
      timestamp: new Date().toISOString()
    });
  }
}

/**
 * Simple hash function for deterministic rollout
 */
function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash;
}