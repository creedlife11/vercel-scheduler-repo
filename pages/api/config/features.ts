import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    // Simple, safe feature flags that can't fail
    const features = {
      enableFairnessReporting: { enabled: true, description: 'Fairness analysis' },
      enableDecisionLogging: { enabled: true, description: 'Decision logging' },
      enableAdvancedValidation: { enabled: true, description: 'Input validation' },
      enablePerformanceMonitoring: { enabled: false, description: 'Performance monitoring' },
      enableInvariantChecking: { enabled: true, description: 'Invariant checking' },
      enableArtifactPanel: { enabled: true, description: 'Artifact panel' },
      enableLeaveManagement: { enabled: true, description: 'Leave management' },
      enablePresetManager: { enabled: true, description: 'Preset manager' },
      enableAuthenticationSystem: { enabled: false, description: 'Authentication' },
      enableRateLimiting: { enabled: false, description: 'Rate limiting' },
      enableTeamStorage: { enabled: false, description: 'Team storage' },
      enableArtifactSharing: { enabled: false, description: 'Artifact sharing' },
      enableExperimentalFeatures: { enabled: false, description: 'Experimental' },
      enableAdvancedAnalytics: { enabled: false, description: 'Analytics' },
      maxWeeksAllowed: 52,
      fairnessThreshold: 0.8,
      maxRequestSizeMB: 2.0,
      enableDarkMode: { enabled: false, description: 'Dark mode' },
      enableKeyboardShortcuts: { enabled: false, description: 'Keyboard shortcuts' },
      enableTooltips: { enabled: false, description: 'Tooltips' }
    };

    const response = {
      features,
      environment: process.env.VERCEL_ENV || 'development',
      timestamp: new Date().toISOString()
    };

    // Cache for 1 minute
    res.setHeader('Cache-Control', 'public, max-age=60');
    res.status(200).json(response);

  } catch (error) {
    // Even if something goes wrong, return safe defaults
    console.error('Features API error:', error);
    
    const safeDefaults = {
      features: {
        enableArtifactPanel: { enabled: true, description: 'Safe default' },
        enableLeaveManagement: { enabled: true, description: 'Safe default' },
        enablePresetManager: { enabled: true, description: 'Safe default' },
        maxWeeksAllowed: 52,
        fairnessThreshold: 0.8,
        maxRequestSizeMB: 2.0
      },
      environment: 'unknown',
      timestamp: new Date().toISOString()
    };
    
    res.status(200).json(safeDefaults);
  }
}