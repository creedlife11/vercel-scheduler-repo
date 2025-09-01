/**
 * React hook for accessing feature flags in the frontend.
 * Provides type-safe access to feature toggles with caching and error handling.
 */

import { useState, useEffect, useCallback } from 'react';

export interface FeatureFlag {
  enabled: boolean;
  rollout_percentage?: number;
  description?: string;
}

export interface FeatureConfig {
  // Core enhanced features
  enableFairnessReporting: FeatureFlag;
  enableDecisionLogging: FeatureFlag;
  enableAdvancedValidation: FeatureFlag;
  enablePerformanceMonitoring: FeatureFlag;
  enableInvariantChecking: FeatureFlag;

  // UI features
  enableArtifactPanel: FeatureFlag;
  enableLeaveManagement: FeatureFlag;
  enablePresetManager: FeatureFlag;

  // Security features
  enableAuthenticationSystem: FeatureFlag;
  enableRateLimiting: FeatureFlag;

  // Gradual rollout features
  enableTeamStorage: FeatureFlag;
  enableArtifactSharing: FeatureFlag;

  // Experimental features
  enableExperimentalFeatures: FeatureFlag;
  enableAdvancedAnalytics: FeatureFlag;

  // UI configuration
  enableDarkMode: FeatureFlag;
  enableKeyboardShortcuts: FeatureFlag;
  enableTooltips: FeatureFlag;

  // Configuration values
  maxWeeksAllowed: number;
  fairnessThreshold: number;
  maxRequestSizeMB: number;
}

interface FeatureConfigResponse {
  features: FeatureConfig;
  environment: string;
  timestamp: string;
}

interface UseFeatureFlagsReturn {
  features: FeatureConfig | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  isEnabled: (flagName: keyof FeatureConfig) => boolean;
  getValue: <T>(flagName: keyof FeatureConfig, defaultValue: T) => T;
}

// Default feature configuration for fallback
const DEFAULT_FEATURES: FeatureConfig = {
  enableFairnessReporting: { enabled: true, description: 'Fairness reporting' },
  enableDecisionLogging: { enabled: true, description: 'Decision logging' },
  enableAdvancedValidation: { enabled: true, description: 'Advanced validation' },
  enablePerformanceMonitoring: { enabled: true, description: 'Performance monitoring' },
  enableInvariantChecking: { enabled: true, description: 'Invariant checking' },
  enableArtifactPanel: { enabled: true, description: 'Artifact panel' },
  enableLeaveManagement: { enabled: true, description: 'Leave management' },
  enablePresetManager: { enabled: true, description: 'Preset manager' },
  enableAuthenticationSystem: { enabled: false, description: 'Authentication system' },
  enableRateLimiting: { enabled: false, description: 'Rate limiting' },
  enableTeamStorage: { enabled: true, description: 'Team storage' },
  enableArtifactSharing: { enabled: true, description: 'Artifact sharing' },
  enableExperimentalFeatures: { enabled: false, description: 'Experimental features' },
  enableAdvancedAnalytics: { enabled: false, description: 'Advanced analytics' },
  enableDarkMode: { enabled: true, description: 'Dark mode' },
  enableKeyboardShortcuts: { enabled: true, description: 'Keyboard shortcuts' },
  enableTooltips: { enabled: true, description: 'Tooltips' },
  maxWeeksAllowed: 52,
  fairnessThreshold: 0.8,
  maxRequestSizeMB: 2.0
};

// Cache for feature flags
let cachedFeatures: FeatureConfig | null = null;
let cacheTimestamp: number = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function useFeatureFlags(): UseFeatureFlagsReturn {
  const [features, setFeatures] = useState<FeatureConfig | null>(cachedFeatures);
  const [loading, setLoading] = useState(!cachedFeatures);
  const [error, setError] = useState<string | null>(null);

  const fetchFeatures = useCallback(async () => {
    // Check cache first
    const now = Date.now();
    if (cachedFeatures && (now - cacheTimestamp) < CACHE_DURATION) {
      setFeatures(cachedFeatures);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/config/features', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include' // Include session cookies
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch feature flags: ${response.status} ${response.statusText}`);
      }

      const data: FeatureConfigResponse = await response.json();
      
      // Merge with defaults to ensure all expected properties exist
      const mergedFeatures = { ...DEFAULT_FEATURES, ...data.features };
      
      // Update cache
      cachedFeatures = mergedFeatures;
      cacheTimestamp = now;
      
      setFeatures(mergedFeatures);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      
      // Use cached features if available, otherwise use defaults
      const fallbackFeatures = cachedFeatures || DEFAULT_FEATURES;
      setFeatures(fallbackFeatures);
      
      console.warn('Failed to fetch feature flags, using fallback:', errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async () => {
    // Clear cache and refetch
    cachedFeatures = null;
    cacheTimestamp = 0;
    await fetchFeatures();
  }, [fetchFeatures]);

  const isEnabled = useCallback((flagName: keyof FeatureConfig): boolean => {
    if (!features) return false;
    
    const flag = features[flagName];
    if (typeof flag === 'object' && flag !== null && 'enabled' in flag) {
      return flag.enabled;
    }
    
    // For non-boolean flags, consider them "enabled" if they have a truthy value
    return Boolean(flag);
  }, [features]);

  const getValue = useCallback(<T>(flagName: keyof FeatureConfig, defaultValue: T): T => {
    if (!features) return defaultValue;
    
    const value = features[flagName];
    if (value === undefined || value === null) {
      return defaultValue;
    }
    
    // If it's a feature flag object, return the enabled status
    if (typeof value === 'object' && 'enabled' in value) {
      return (value.enabled as unknown) as T;
    }
    
    return value as T;
  }, [features]);

  // Fetch features on mount
  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  return {
    features,
    loading,
    error,
    refetch,
    isEnabled,
    getValue
  };
}

// Convenience hooks for specific feature checks
export function useIsFairnessReportingEnabled(): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled('enableFairnessReporting');
}

export function useIsDecisionLoggingEnabled(): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled('enableDecisionLogging');
}

export function useIsArtifactPanelEnabled(): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled('enableArtifactPanel');
}

export function useIsLeaveManagementEnabled(): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled('enableLeaveManagement');
}

export function useIsPresetManagerEnabled(): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled('enablePresetManager');
}

export function useMaxWeeksAllowed(): number {
  const { getValue } = useFeatureFlags();
  return getValue('maxWeeksAllowed', 52);
}

export function useFairnessThreshold(): number {
  const { getValue } = useFeatureFlags();
  return getValue('fairnessThreshold', 0.8);
}

// Higher-order component for conditional rendering based on feature flags
export function withFeatureFlag<P extends object>(
  Component: React.ComponentType<P>,
  flagName: keyof FeatureConfig,
  fallback?: React.ComponentType<P> | React.ReactElement | null
) {
  return function FeatureFlagWrapper(props: P) {
    const { isEnabled, loading } = useFeatureFlags();
    
    if (loading) {
      return <div>Loading...</div>;
    }
    
    if (!isEnabled(flagName)) {
      if (fallback) {
        if (React.isValidElement(fallback)) {
          return fallback;
        }
        const FallbackComponent = fallback as React.ComponentType<P>;
        return <FallbackComponent {...props} />;
      }
      return null;
    }
    
    return <Component {...props} />;
  };
}