# Feature Flag Configuration Guide

This guide explains how to configure and manage feature flags in the Enhanced Team Scheduler application.

## Table of Contents

- [Overview](#overview)
- [Feature Flag System](#feature-flag-system)
- [Configuration Methods](#configuration-methods)
- [Available Feature Flags](#available-feature-flags)
- [Rollout Strategies](#rollout-strategies)
- [Management Procedures](#management-procedures)
- [Monitoring and Analytics](#monitoring-and-analytics)
- [Best Practices](#best-practices)

## Overview

The Enhanced Team Scheduler uses a comprehensive feature flag system to enable:

- **Gradual Rollouts**: Deploy features to a percentage of users
- **Environment Control**: Different features for dev/staging/production
- **Quick Rollbacks**: Disable features without code deployment
- **A/B Testing**: Test different feature variations
- **User Targeting**: Enable features for specific user groups

## Feature Flag System

### Architecture

```
Frontend (React) → Feature Flag Hook → API Endpoint → Feature Flag Manager → Edge Config/Environment Variables
```

### Components

1. **Frontend Hook** (`useFeatureFlags`): React hook for accessing feature flags
2. **API Endpoint** (`/api/config/features`): Serves feature configuration to frontend
3. **Feature Flag Manager** (`lib/feature_flags.py`): Backend feature flag logic
4. **Edge Config**: Vercel's distributed configuration store (recommended)
5. **Environment Variables**: Fallback configuration method

## Configuration Methods

### Method 1: Vercel Edge Config (Recommended)

Edge Config provides the fastest and most reliable feature flag delivery.

#### Setup

1. **Create Edge Config**:
   ```bash
   vercel edge-config create scheduler-features
   ```

2. **Set Environment Variables**:
   ```bash
   vercel env add EDGE_CONFIG <edge-config-id>
   vercel env add EDGE_CONFIG_TOKEN <edge-config-token>
   ```

3. **Update Configuration**:
   ```bash
   # Generate feature flag JSON
   npm run deploy:edge-config > features.json
   
   # Upload to Edge Config
   vercel edge-config update <edge-config-id> --file features.json
   ```

#### Edge Config Format

```json
{
  "enableFairnessReporting": {
    "enabled": true,
    "rollout_percentage": 100,
    "environments": ["development", "preview", "production"],
    "description": "Enable fairness analysis and reporting"
  },
  "enableTeamStorage": {
    "enabled": true,
    "rollout_percentage": 50,
    "environments": ["production"],
    "description": "Enable team-scoped artifact storage"
  },
  "maxWeeksAllowed": 52,
  "fairnessThreshold": 0.8
}
```

### Method 2: Environment Variables

Environment variables provide a simple fallback configuration method.

#### Setup

```bash
# Boolean flags
vercel env add ENABLE_FAIRNESS_REPORTING true
vercel env add ENABLE_DECISION_LOGGING true
vercel env add ENABLE_TEAM_STORAGE false

# Configuration values
vercel env add MAX_WEEKS_ALLOWED 52
vercel env add FAIRNESS_THRESHOLD 0.8
vercel env add MAX_REQUEST_SIZE_MB 2.0

# Rollout percentages (0-100)
vercel env add ROLLOUT_TEAM_STORAGE 50
vercel env add ROLLOUT_ARTIFACT_SHARING 75
```

## Available Feature Flags

### Core Enhanced Features

#### `enableFairnessReporting`
- **Description**: Enable fairness analysis and reporting in schedule generation
- **Default**: `true` (100% rollout)
- **Impact**: Shows fairness metrics in artifact panel
- **Dependencies**: None

#### `enableDecisionLogging`
- **Description**: Enable detailed decision logging during schedule generation
- **Default**: `true` (100% rollout)
- **Impact**: Provides decision rationale in logs and exports
- **Dependencies**: None

#### `enableAdvancedValidation`
- **Description**: Enable enhanced input validation with name hygiene
- **Default**: `true` (100% rollout)
- **Impact**: Better input validation and error messages
- **Dependencies**: None

#### `enablePerformanceMonitoring`
- **Description**: Enable performance monitoring and metrics collection
- **Default**: `true` (100% rollout)
- **Impact**: Collects timing and memory usage metrics
- **Dependencies**: None

#### `enableInvariantChecking`
- **Description**: Enable scheduling invariant validation
- **Default**: `true` (100% rollout)
- **Impact**: Validates schedule correctness and logs violations
- **Dependencies**: None

### UI Features

#### `enableArtifactPanel`
- **Description**: Enable enhanced artifact panel with multiple format tabs
- **Default**: `true` (100% rollout)
- **Impact**: Shows tabbed interface for CSV/XLSX/JSON/Fairness/Decisions
- **Dependencies**: `enableFairnessReporting`, `enableDecisionLogging`

#### `enableLeaveManagement`
- **Description**: Enable leave management with CSV/XLSX import
- **Default**: `true` (100% rollout)
- **Impact**: Shows leave management interface
- **Dependencies**: None

#### `enablePresetManager`
- **Description**: Enable preset configuration system
- **Default**: `true` (100% rollout)
- **Impact**: Shows preset save/load functionality
- **Dependencies**: None

### Security Features

#### `enableAuthenticationSystem`
- **Description**: Enable authentication and authorization system
- **Default**: `false` (development), `true` (preview/production)
- **Impact**: Requires user login and role-based access
- **Dependencies**: NextAuth.js configuration

#### `enableRateLimiting`
- **Description**: Enable request rate limiting and security controls
- **Default**: `false` (development), `true` (preview/production)
- **Impact**: Limits requests per user/IP
- **Dependencies**: None

### Gradual Rollout Features

#### `enableTeamStorage`
- **Description**: Enable team-scoped artifact storage
- **Default**: `true` (50% rollout in production)
- **Impact**: Stores generated artifacts per team
- **Dependencies**: Authentication system

#### `enableArtifactSharing`
- **Description**: Enable artifact sharing between team members
- **Default**: `true` (75% rollout in production)
- **Impact**: Allows sharing of generated schedules
- **Dependencies**: `enableTeamStorage`, authentication

### Experimental Features

#### `enableExperimentalFeatures`
- **Description**: Enable experimental features for testing
- **Default**: `true` (development only)
- **Impact**: Shows experimental UI elements and features
- **Dependencies**: None

#### `enableAdvancedAnalytics`
- **Description**: Enable advanced analytics and insights
- **Default**: `false` (not yet implemented)
- **Impact**: Future analytics features
- **Dependencies**: None

### Configuration Values

#### `maxWeeksAllowed`
- **Description**: Maximum weeks allowed in schedule generation
- **Default**: `52` (production), `104` (development)
- **Type**: Integer (1-104)

#### `fairnessThreshold`
- **Description**: Threshold for fairness scoring (Gini coefficient)
- **Default**: `0.8` (production), `0.5` (development)
- **Type**: Float (0.0-1.0)

#### `maxRequestSizeMB`
- **Description**: Maximum request body size in megabytes
- **Default**: `2.0` (production), `5.0` (development)
- **Type**: Float

## Rollout Strategies

### Percentage Rollouts

Control feature exposure by percentage of users:

```json
{
  "enableNewFeature": {
    "enabled": true,
    "rollout_percentage": 25,
    "description": "25% of users see the new feature"
  }
}
```

### Environment-Based Rollouts

Enable features only in specific environments:

```json
{
  "enableBetaFeature": {
    "enabled": true,
    "rollout_percentage": 100,
    "environments": ["development", "preview"],
    "description": "Only in dev and staging"
  }
}
```

### User Group Targeting

Target specific user groups (requires authentication):

```json
{
  "enableAdminFeature": {
    "enabled": true,
    "rollout_percentage": 100,
    "user_groups": ["admin", "power_user"],
    "description": "Only for admin and power users"
  }
}
```

### Rollout Phases

#### Phase 1: Development (0% production users)
```json
{
  "enabled": true,
  "rollout_percentage": 100,
  "environments": ["development"]
}
```

#### Phase 2: Preview Testing (0% production users)
```json
{
  "enabled": true,
  "rollout_percentage": 100,
  "environments": ["development", "preview"]
}
```

#### Phase 3: Limited Production (10% production users)
```json
{
  "enabled": true,
  "rollout_percentage": 10,
  "environments": ["development", "preview", "production"]
}
```

#### Phase 4: Gradual Rollout (50% production users)
```json
{
  "enabled": true,
  "rollout_percentage": 50,
  "environments": ["development", "preview", "production"]
}
```

#### Phase 5: Full Rollout (100% production users)
```json
{
  "enabled": true,
  "rollout_percentage": 100,
  "environments": ["development", "preview", "production"]
}
```

## Management Procedures

### Adding New Feature Flags

1. **Define the Flag**:
   ```typescript
   // Add to lib/hooks/useFeatureFlags.ts
   export interface FeatureConfig {
     // ... existing flags
     enableNewFeature: FeatureFlag;
   }
   ```

2. **Add Default Configuration**:
   ```typescript
   const DEFAULT_FEATURES: FeatureConfig = {
     // ... existing defaults
     enableNewFeature: { enabled: false, description: 'New feature description' }
   };
   ```

3. **Update API Endpoint**:
   ```typescript
   // Add to pages/api/config/features.ts
   const features: FeatureConfig = {
     // ... existing features
     enableNewFeature: {
       enabled: environment === 'development',
       rollout_percentage: 0,
       description: 'New feature for testing'
     }
   };
   ```

4. **Add Backend Support** (if needed):
   ```python
   # Add to lib/feature_flags.py
   def is_new_feature_enabled(user_id: str = None) -> bool:
       return feature_flags.is_enabled("enableNewFeature", user_id)
   ```

### Updating Feature Flags

#### Via Edge Config
```bash
# Update single flag
vercel edge-config update <edge-config-id> --set enableNewFeature='{"enabled":true,"rollout_percentage":25}'

# Update multiple flags
npm run deploy:edge-config > features.json
# Edit features.json
vercel edge-config update <edge-config-id> --file features.json
```

#### Via Environment Variables
```bash
# Enable feature
vercel env add ENABLE_NEW_FEATURE true

# Set rollout percentage
vercel env add ROLLOUT_NEW_FEATURE 25

# Update configuration value
vercel env add MAX_WEEKS_ALLOWED 104
```

### Removing Feature Flags

1. **Disable the Flag**:
   ```bash
   vercel edge-config update <edge-config-id> --set enableOldFeature='{"enabled":false}'
   ```

2. **Remove from Code** (after confirming disabled):
   ```bash
   # Remove feature flag checks from code
   # Remove from configuration interfaces
   # Clean up unused code paths
   ```

3. **Clean Up Configuration**:
   ```bash
   # Remove from Edge Config
   vercel edge-config update <edge-config-id> --delete enableOldFeature
   
   # Remove environment variables
   vercel env rm ENABLE_OLD_FEATURE
   ```

## Monitoring and Analytics

### Feature Flag Usage Tracking

Monitor feature flag usage in logs:

```bash
# View feature flag usage
vercel logs --grep "feature_flag" | head -20

# Count flag usage by type
vercel logs --since 24h --grep "feature_flag" | \
  grep -o "\"flag\":\"[^\"]*\"" | \
  sort | uniq -c | sort -nr

# Monitor rollout effectiveness
vercel logs --since 24h --grep "rollout_percentage" | \
  grep -o "\"rollout_percentage\":[0-9]*" | \
  sort | uniq -c
```

### Performance Impact

Monitor feature flag performance:

```bash
# Feature flag API response times
curl -w "Feature flags response time: %{time_total}s\n" \
  -s -o /dev/null https://your-app.vercel.app/api/config/features

# Edge Config performance
vercel logs --grep "edge_config.*time"
```

### A/B Testing Analysis

Track feature effectiveness:

```bash
# Compare error rates with/without feature
vercel logs --since 24h --grep "enableNewFeature.*true" | grep "ERROR" | wc -l
vercel logs --since 24h --grep "enableNewFeature.*false" | grep "ERROR" | wc -l

# Compare performance metrics
vercel logs --since 24h --grep "enableNewFeature.*true" | \
  grep -o "processing_time_ms\":[0-9]*" | \
  awk -F: '{sum+=$2; count++} END {print "With feature: " sum/count "ms"}'
```

## Best Practices

### Naming Conventions

- Use descriptive, action-oriented names: `enableFeatureName`
- Include the action: `enable`, `show`, `allow`, `use`
- Be specific: `enableArtifactPanel` not `enablePanel`
- Use camelCase for consistency

### Flag Lifecycle

1. **Development**: Test with 100% rollout in development
2. **Preview**: Test with 100% rollout in staging
3. **Canary**: Start with 1-5% in production
4. **Gradual**: Increase to 25%, 50%, 75%
5. **Full**: Deploy to 100% of users
6. **Cleanup**: Remove flag after stable deployment

### Configuration Management

- **Document all flags**: Include description and dependencies
- **Set expiration dates**: Plan flag removal timeline
- **Monitor usage**: Track flag effectiveness and performance
- **Regular cleanup**: Remove unused flags quarterly

### Emergency Procedures

#### Quick Disable
```bash
# Disable problematic feature immediately
vercel edge-config update <edge-config-id> --set enableProblematicFeature='{"enabled":false}'
```

#### Rollback Rollout
```bash
# Reduce rollout percentage
vercel edge-config update <edge-config-id> --set enableNewFeature='{"enabled":true,"rollout_percentage":0}'
```

#### Emergency Override
```bash
# Use environment variable to override Edge Config
vercel env add EMERGENCY_DISABLE_NEW_FEATURE true
```

### Testing Strategies

#### Local Testing
```bash
# Test with feature enabled
ENABLE_NEW_FEATURE=true npm run dev

# Test with feature disabled
ENABLE_NEW_FEATURE=false npm run dev
```

#### Preview Testing
```bash
# Deploy to preview with feature enabled
vercel --env ENABLE_NEW_FEATURE=true

# Test both enabled and disabled states
```

#### Production Testing
```bash
# Start with small rollout
vercel edge-config update <edge-config-id> --set enableNewFeature='{"enabled":true,"rollout_percentage":1}'

# Monitor for issues
vercel logs --follow --grep "enableNewFeature"

# Gradually increase rollout
```

### Security Considerations

- **Sensitive Features**: Use authentication-gated flags for sensitive features
- **Data Access**: Ensure flags don't expose unauthorized data
- **Rate Limiting**: Consider impact on rate limiting and security controls
- **Audit Trail**: Log all feature flag changes for security auditing

---

For additional help with feature flags, consult the [deployment guide](./DEPLOYMENT.md) or [troubleshooting guide](./TROUBLESHOOTING.md).