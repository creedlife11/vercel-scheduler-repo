# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Enhanced Team Scheduler application.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Error Codes](#error-codes)
- [Performance Issues](#performance-issues)
- [Feature Flag Issues](#feature-flag-issues)
- [Authentication Problems](#authentication-problems)
- [Database Issues](#database-issues)
- [Deployment Problems](#deployment-problems)
- [Monitoring and Debugging](#monitoring-and-debugging)

## Quick Diagnostics

### Health Check Commands

```bash
# Basic health check
curl https://your-app.vercel.app/api/healthz

# Detailed readiness check
curl https://your-app.vercel.app/api/readyz

# Feature configuration
curl https://your-app.vercel.app/api/config/features

# Performance metrics (if enabled)
curl https://your-app.vercel.app/api/metrics
```

### Configuration Validation

```bash
# Validate environment setup
npm run deploy:validate

# View current configuration
npm run deploy:config

# Check feature flags
npm run deploy:edge-config
```

### Log Analysis

```bash
# View recent logs
vercel logs

# Filter for errors
vercel logs --grep "ERROR"

# Filter by request ID
vercel logs --grep "request_id.*abc123"
```

## Common Issues

### 1. Schedule Generation Fails

**Symptoms:**
- 500 Internal Server Error
- "Schedule generation failed" message
- Empty or malformed CSV output

**Diagnosis:**
```bash
# Check logs for schedule generation errors
vercel logs --grep "schedule_generation.*failed"

# Verify input validation
curl -X POST https://your-app.vercel.app/api/generate \
  -H "Content-Type: application/json" \
  -d '{"engineers":["A","B","C","D","E","F"],"start_sunday":"2025-01-05","weeks":2}'
```

**Solutions:**
1. **Invalid Input Data:**
   ```bash
   # Check engineer names are unique and valid
   # Ensure start_sunday is actually a Sunday
   # Verify weeks is between 1-52
   ```

2. **Leave Data Issues:**
   ```bash
   # Ensure leave dates are valid
   # Check engineer names in leave match engineer list
   # Verify date format is YYYY-MM-DD
   ```

3. **Memory/Timeout Issues:**
   ```bash
   # Reduce weeks or engineer count
   # Check Vercel function limits
   vercel inspect <deployment-url>
   ```

### 2. Authentication Not Working

**Symptoms:**
- Redirect loops on login
- "Authentication required" errors
- Session not persisting

**Diagnosis:**
```bash
# Check authentication configuration
vercel env get NEXTAUTH_SECRET
vercel env get NEXTAUTH_URL
vercel env get ENABLE_AUTH

# Test authentication endpoint
curl https://your-app.vercel.app/api/auth/session
```

**Solutions:**
1. **Missing Environment Variables:**
   ```bash
   vercel env add NEXTAUTH_SECRET $(openssl rand -base64 32)
   vercel env add NEXTAUTH_URL https://your-app.vercel.app
   ```

2. **URL Mismatch:**
   ```bash
   # Ensure NEXTAUTH_URL matches deployment URL
   # Update OAuth provider callback URLs
   ```

3. **Provider Configuration:**
   ```bash
   # Check OAuth client ID and secret
   # Verify provider callback URLs
   # Ensure provider is enabled
   ```

### 3. Feature Flags Not Working

**Symptoms:**
- Features not appearing/disappearing as expected
- Default values being used instead of configured values
- Feature flag API returning errors

**Diagnosis:**
```bash
# Check feature flag configuration
curl https://your-app.vercel.app/api/config/features

# Verify Edge Config setup
vercel edge-config get <edge-config-id>

# Check environment variables
vercel env ls | grep FEATURE
```

**Solutions:**
1. **Edge Config Issues:**
   ```bash
   # Verify Edge Config ID and token
   vercel env get EDGE_CONFIG
   vercel env get EDGE_CONFIG_TOKEN
   
   # Update Edge Config
   npm run deploy:edge-config > features.json
   vercel edge-config update <edge-config-id> --file features.json
   ```

2. **Cache Issues:**
   ```bash
   # Clear feature flag cache
   # Wait 5 minutes for cache expiry
   # Or redeploy to force refresh
   vercel redeploy
   ```

3. **Rollout Percentage:**
   ```bash
   # Check if user is in rollout percentage
   # Verify rollout logic in feature flag code
   ```

### 4. Database Connection Problems

**Symptoms:**
- "Database connection failed" errors
- Timeouts on database operations
- Connection pool exhausted

**Diagnosis:**
```bash
# Check database URL
vercel env get DATABASE_URL

# Test database connectivity
# (Run from local environment with same DATABASE_URL)
psql $DATABASE_URL -c "SELECT 1;"
```

**Solutions:**
1. **Connection String Issues:**
   ```bash
   # Verify database URL format
   # postgresql://user:password@host:port/database?sslmode=require
   
   # Check SSL requirements
   # Ensure user has proper permissions
   ```

2. **Connection Limits:**
   ```bash
   # Check database connection limits
   # Reduce max connections in config
   vercel env add MAX_DB_CONNECTIONS 10
   ```

3. **Network Issues:**
   ```bash
   # Verify database server is accessible
   # Check firewall rules
   # Ensure Vercel IPs are whitelisted
   ```

### 5. Rate Limiting Too Aggressive

**Symptoms:**
- 429 "Rate limit exceeded" errors
- Legitimate requests being blocked
- Users unable to generate schedules

**Diagnosis:**
```bash
# Check rate limiting configuration
vercel env get ENABLE_RATE_LIMITING
vercel env get RATE_LIMIT_HOUR
vercel env get RATE_LIMIT_MINUTE

# Look for rate limit errors in logs
vercel logs --grep "rate.*limit.*exceeded"
```

**Solutions:**
1. **Increase Limits:**
   ```bash
   vercel env add RATE_LIMIT_HOUR 200
   vercel env add RATE_LIMIT_MINUTE 20
   vercel env add RATE_LIMIT_BURST 30
   ```

2. **Disable Temporarily:**
   ```bash
   vercel env add ENABLE_RATE_LIMITING false
   ```

3. **User-Specific Limits:**
   ```bash
   # Check if admin users have higher limits
   # Verify user role detection
   ```

## Error Codes

### HTTP Status Codes

| Code | Meaning | Common Causes | Solutions |
|------|---------|---------------|-----------|
| 400 | Bad Request | Invalid input data, malformed JSON | Validate input format, check required fields |
| 401 | Unauthorized | Authentication required, invalid session | Check auth configuration, verify login |
| 403 | Forbidden | Insufficient permissions | Verify user roles, check authorization |
| 422 | Unprocessable Entity | Validation errors | Fix input validation errors |
| 429 | Too Many Requests | Rate limit exceeded | Increase limits or wait |
| 500 | Internal Server Error | Application error, database issues | Check logs, verify configuration |
| 502 | Bad Gateway | Vercel function timeout/error | Check function limits, optimize code |
| 503 | Service Unavailable | Temporary service issues | Wait and retry, check Vercel status |

### Application Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `VALIDATION_ERROR` | Input validation failed | Fix input data format |
| `AUTHENTICATION_ERROR` | Authentication failed | Check auth configuration |
| `AUTHORIZATION_ERROR` | Insufficient permissions | Verify user roles |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait or increase limits |
| `SCHEDULE_GENERATION_ERROR` | Schedule creation failed | Check input parameters |
| `EXPORT_ERROR` | File export failed | Verify export format |
| `DATABASE_ERROR` | Database operation failed | Check database connectivity |
| `FEATURE_FLAG_ERROR` | Feature flag lookup failed | Verify feature flag configuration |

## Performance Issues

### Slow Response Times

**Symptoms:**
- API requests taking > 5 seconds
- Frontend loading slowly
- Timeouts on large schedules

**Diagnosis:**
```bash
# Check performance metrics
curl https://your-app.vercel.app/api/metrics

# Look for slow operations in logs
vercel logs --grep "processing_time_ms.*[5-9][0-9]{3}"

# Monitor function execution time
vercel logs --grep "Duration:"
```

**Solutions:**
1. **Optimize Schedule Generation:**
   ```bash
   # Reduce weeks or engineer count
   # Enable performance monitoring to identify bottlenecks
   vercel env add ENABLE_PERFORMANCE_MONITORING true
   ```

2. **Database Optimization:**
   ```bash
   # Enable connection pooling
   # Add database indexes
   # Optimize queries
   ```

3. **Caching:**
   ```bash
   # Enable feature flag caching
   # Cache static responses
   # Use CDN for assets
   ```

### Memory Issues

**Symptoms:**
- Out of memory errors
- Function crashes
- Incomplete responses

**Diagnosis:**
```bash
# Check memory usage in logs
vercel logs --grep "memory"

# Monitor function limits
vercel inspect <deployment-url>
```

**Solutions:**
```bash
# Increase function memory in vercel.json
{
  "functions": {
    "api/*.py": {
      "memory": 2048
    }
  }
}

# Optimize memory usage in code
# Process data in chunks
# Clear unused variables
```

## Feature Flag Issues

### Features Not Appearing

**Diagnosis Steps:**
1. Check feature flag API response
2. Verify user is in rollout percentage
3. Check environment restrictions
4. Validate Edge Config setup

**Debug Commands:**
```bash
# Test feature flag API
curl https://your-app.vercel.app/api/config/features

# Check specific feature
curl https://your-app.vercel.app/api/config/features | jq '.features.enableArtifactPanel'

# Verify Edge Config
vercel edge-config get <edge-config-id>
```

### Rollout Issues

**Common Problems:**
- User not in rollout percentage
- Environment restrictions
- Cache not updated

**Solutions:**
```bash
# Force user into rollout (for testing)
# Modify rollout percentage
# Clear cache by redeploying
vercel redeploy
```

## Authentication Problems

### Login Redirects

**Symptoms:**
- Infinite redirect loops
- "Callback URL mismatch" errors
- Login button not working

**Solutions:**
1. **Check Callback URLs:**
   ```bash
   # Ensure OAuth provider has correct callback URL
   # https://your-app.vercel.app/api/auth/callback/[provider]
   ```

2. **Verify NEXTAUTH_URL:**
   ```bash
   vercel env get NEXTAUTH_URL
   # Should match deployment URL exactly
   ```

3. **Provider Configuration:**
   ```bash
   # Check OAuth client credentials
   # Verify provider is enabled
   # Test provider endpoints
   ```

### Session Issues

**Symptoms:**
- Sessions not persisting
- Frequent logouts
- "Invalid session" errors

**Solutions:**
```bash
# Check session configuration
# Verify NEXTAUTH_SECRET is set
vercel env get NEXTAUTH_SECRET

# Increase session max age
vercel env add NEXTAUTH_MAX_AGE 86400

# Check cookie settings
# Verify HTTPS is enabled
```

## Database Issues

### Connection Failures

**Common Causes:**
- Invalid connection string
- SSL/TLS issues
- Network connectivity
- Authentication failures

**Diagnostic Steps:**
```bash
# Test connection string format
echo $DATABASE_URL | grep -E "postgresql://.*:.*@.*:.*/.+"

# Test SSL connection
psql "$DATABASE_URL" -c "SELECT version();"

# Check connection limits
psql "$DATABASE_URL" -c "SHOW max_connections;"
```

### Migration Issues

**Symptoms:**
- Database schema out of sync
- Missing tables/columns
- Migration failures

**Solutions:**
```bash
# Check migration status
npx prisma migrate status

# Apply pending migrations
npx prisma migrate deploy

# Reset database (development only)
npx prisma migrate reset
```

## Deployment Problems

### Build Failures

**Common Issues:**
- TypeScript errors
- Missing dependencies
- Environment variable issues

**Solutions:**
```bash
# Check build logs
vercel logs --build

# Run build locally
npm run build

# Fix TypeScript errors
npm run type-check

# Install missing dependencies
npm install
```

### Function Timeouts

**Symptoms:**
- 502 Bad Gateway errors
- "Function execution timed out"
- Incomplete responses

**Solutions:**
```bash
# Increase function timeout in vercel.json
{
  "functions": {
    "api/*.py": {
      "maxDuration": 60
    }
  }
}

# Optimize function performance
# Break down large operations
# Use async processing
```

## Monitoring and Debugging

### Enable Debug Mode

```bash
# Enable debug logging
vercel env add LOG_LEVEL DEBUG
vercel env add DEBUG_MODE true

# Enable performance monitoring
vercel env add ENABLE_PERFORMANCE_MONITORING true
```

### Log Analysis Patterns

```bash
# Find errors by request ID
vercel logs --grep "request_id.*abc123"

# Monitor authentication
vercel logs --grep "authentication"

# Track feature flag usage
vercel logs --grep "feature_flag"

# Performance monitoring
vercel logs --grep "processing_time_ms"

# Database operations
vercel logs --grep "database"
```

### Performance Profiling

```bash
# Monitor API response times
curl -w "@curl-format.txt" -s -o /dev/null https://your-app.vercel.app/api/generate

# Create curl-format.txt:
echo "     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n" > curl-format.txt
```

### Health Monitoring

```bash
# Set up monitoring script
#!/bin/bash
while true; do
  status=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/healthz)
  if [ $status -ne 200 ]; then
    echo "$(date): Health check failed with status $status"
  fi
  sleep 60
done
```

## Getting Help

### Before Contacting Support

1. Check this troubleshooting guide
2. Review deployment documentation
3. Search existing GitHub issues
4. Check Vercel status page
5. Verify configuration with validation commands

### Information to Include

When reporting issues, include:

- Environment (development/preview/production)
- Error messages and stack traces
- Request ID from logs
- Steps to reproduce
- Configuration (sanitized)
- Browser/client information

### Support Channels

- **GitHub Issues**: Technical problems and bugs
- **Vercel Support**: Deployment and platform issues
- **Documentation**: Check docs for configuration help

### Emergency Procedures

For critical production issues:

1. **Immediate Rollback:**
   ```bash
   vercel rollback <previous-deployment-url>
   ```

2. **Disable Problematic Features:**
   ```bash
   vercel env add ENABLE_PROBLEMATIC_FEATURE false
   ```

3. **Scale Down:**
   ```bash
   # Reduce rate limits temporarily
   vercel env add RATE_LIMIT_HOUR 50
   ```

4. **Monitor Recovery:**
   ```bash
   # Watch logs for improvement
   vercel logs --follow
   ```