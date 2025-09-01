# Deployment Guide

This guide covers deploying the Enhanced Team Scheduler application to various environments with proper configuration and monitoring setup.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Vercel Deployment](#vercel-deployment)
- [Feature Flag Configuration](#feature-flag-configuration)
- [Database Setup](#database-setup)
- [Authentication Configuration](#authentication-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)

## Overview

The Enhanced Team Scheduler supports three deployment environments:

- **Development**: Local development with minimal security, all features enabled
- **Preview**: Staging environment with full security, gradual feature rollouts
- **Production**: Live environment with maximum security, controlled feature rollouts

## Prerequisites

### Required Tools

- Node.js 18+ and npm
- Python 3.11+
- Vercel CLI (for deployment)
- Git

### Required Accounts

- [Vercel](https://vercel.com) account for hosting
- [PostgreSQL](https://www.postgresql.org/) database (production/preview)
- [Auth0](https://auth0.com/) or similar for authentication (optional)

## Environment Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd scheduler-app
npm install
```

### 2. Environment Configuration

Copy the appropriate environment file:

```bash
# For development
cp .env.development .env.local

# For production
cp .env.production.example .env.production
```

### 3. Validate Configuration

```bash
# Validate environment variables
npm run deploy:validate

# View current configuration
npm run deploy:config
```

## Vercel Deployment

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login and Link Project

```bash
vercel login
vercel link
```

### 3. Configure Environment Variables

Set required environment variables in Vercel dashboard or CLI:

```bash
# Required for all environments
vercel env add NEXTAUTH_SECRET
vercel env add NEXTAUTH_URL

# Required for production
vercel env add DATABASE_URL
vercel env add ALLOWED_DOMAINS

# Optional but recommended
vercel env add EDGE_CONFIG
vercel env add EDGE_CONFIG_TOKEN
```

### 4. Deploy

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 5. Post-Deployment Setup

```bash
# Run deployment setup
npm run deploy:setup
```

## Feature Flag Configuration

### Using Vercel Edge Config (Recommended)

1. **Create Edge Config**:
   ```bash
   vercel edge-config create scheduler-features
   ```

2. **Get Configuration**:
   ```bash
   # Get Edge Config ID and token from Vercel dashboard
   vercel env add EDGE_CONFIG <edge-config-id>
   vercel env add EDGE_CONFIG_TOKEN <edge-config-token>
   ```

3. **Update Feature Flags**:
   ```bash
   # Generate and upload feature flags
   npm run deploy:edge-config > features.json
   vercel edge-config update <edge-config-id> --file features.json
   ```

### Manual Configuration

Set feature flags via environment variables:

```bash
# Core features (usually enabled)
vercel env add ENABLE_FAIRNESS_REPORTING true
vercel env add ENABLE_DECISION_LOGGING true
vercel env add ENABLE_ADVANCED_VALIDATION true

# Security features (environment-dependent)
vercel env add ENABLE_AUTHENTICATION_SYSTEM true
vercel env add ENABLE_RATE_LIMITING true

# Gradual rollout features
vercel env add ENABLE_TEAM_STORAGE true
vercel env add ENABLE_ARTIFACT_SHARING true

# Configuration values
vercel env add MAX_WEEKS_ALLOWED 52
vercel env add FAIRNESS_THRESHOLD 0.8
vercel env add MAX_REQUEST_SIZE_MB 2.0
```

## Database Setup

### Development (SQLite)

No setup required - uses local file database.

### Production/Preview (PostgreSQL)

1. **Create Database**:
   ```sql
   CREATE DATABASE scheduler_app;
   CREATE USER scheduler_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE scheduler_app TO scheduler_user;
   ```

2. **Set Database URL**:
   ```bash
   vercel env add DATABASE_URL "postgresql://scheduler_user:secure_password@host:5432/scheduler_app?sslmode=require"
   ```

3. **Run Migrations** (if using Prisma):
   ```bash
   npx prisma migrate deploy
   ```

## Authentication Configuration

### NextAuth.js Setup

1. **Generate Secret**:
   ```bash
   openssl rand -base64 32
   vercel env add NEXTAUTH_SECRET <generated-secret>
   ```

2. **Set URL**:
   ```bash
   vercel env add NEXTAUTH_URL https://your-domain.vercel.app
   ```

3. **Configure Providers** (in `pages/api/auth/[...nextauth].ts`):
   ```typescript
   providers: [
     GoogleProvider({
       clientId: process.env.GOOGLE_CLIENT_ID,
       clientSecret: process.env.GOOGLE_CLIENT_SECRET,
     }),
     // Add other providers as needed
   ]
   ```

### Domain Restrictions

```bash
# Restrict access to specific domains
vercel env add ALLOWED_DOMAINS "company.com,partner.com"
```

## Monitoring Setup

### Structured Logging

Logs are automatically structured in JSON format. Configure log level:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
vercel env add LOG_LEVEL INFO
```

### Performance Monitoring

Enable performance tracking:

```bash
vercel env add ENABLE_PERFORMANCE_MONITORING true
```

### Health Endpoints

The application provides health check endpoints:

- `/api/healthz` - Basic health check
- `/api/readyz` - Readiness check with dependencies
- `/api/metrics` - Performance metrics (if enabled)

### External Monitoring

Configure external monitoring services:

```bash
# Sentry for error tracking
vercel env add SENTRY_DSN <your-sentry-dsn>

# Custom analytics
vercel env add ANALYTICS_ID <your-analytics-id>
```

## Security Configuration

### Rate Limiting

Configure rate limits based on environment:

```bash
# Production limits
vercel env add RATE_LIMIT_HOUR 100
vercel env add RATE_LIMIT_MINUTE 10
vercel env add RATE_LIMIT_BURST 20

# Enable rate limiting
vercel env add ENABLE_RATE_LIMITING true
```

### CORS Configuration

```bash
# Set allowed origins
vercel env add CORS_ORIGINS "https://your-domain.com,https://admin.your-domain.com"
```

### Request Size Limits

```bash
# Set maximum request size (in MB)
vercel env add MAX_REQUEST_SIZE_MB 2.0
```

### Content Security Policy

The application includes security headers in `vercel.json`. Customize as needed:

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline'"
        }
      ]
    }
  ]
}
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.local
VERCEL_ENV=development
ENABLE_AUTH=false
ENABLE_RATE_LIMITING=false
LOG_LEVEL=DEBUG
MAX_WEEKS_ALLOWED=104
ENABLE_EXPERIMENTAL_FEATURES=true
```

### Preview Environment

```bash
# Vercel environment variables
VERCEL_ENV=preview
ENABLE_AUTH=true
ENABLE_RATE_LIMITING=true
LOG_LEVEL=INFO
MAX_WEEKS_ALLOWED=52
ENABLE_EXPERIMENTAL_FEATURES=false
```

### Production Environment

```bash
# Vercel environment variables
VERCEL_ENV=production
ENABLE_AUTH=true
ENABLE_RATE_LIMITING=true
LOG_LEVEL=INFO
MAX_WEEKS_ALLOWED=52
ENABLE_EXPERIMENTAL_FEATURES=false
ENABLE_METRICS=false  # Disable public metrics in production
```

## Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] Database setup complete
- [ ] Authentication configured
- [ ] Feature flags defined
- [ ] Security settings reviewed
- [ ] Tests passing (`npm test`)
- [ ] Type checking passed (`npm run type-check`)
- [ ] Linting passed (`npm run lint`)

### Post-Deployment

- [ ] Health checks responding (`/api/healthz`, `/api/readyz`)
- [ ] Authentication working
- [ ] Feature flags active
- [ ] Monitoring configured
- [ ] Error tracking setup
- [ ] Performance metrics collected
- [ ] Security headers present

### Verification Commands

```bash
# Check deployment status
vercel ls

# View logs
vercel logs <deployment-url>

# Test health endpoints
curl https://your-app.vercel.app/api/healthz
curl https://your-app.vercel.app/api/readyz

# Validate configuration
npm run deploy:validate
```

## Rollback Procedures

### Quick Rollback

```bash
# Rollback to previous deployment
vercel rollback <previous-deployment-url>
```

### Feature Flag Rollback

```bash
# Disable problematic feature
vercel edge-config update <edge-config-id> --set enableProblematicFeature=false

# Or via environment variable
vercel env rm ENABLE_PROBLEMATIC_FEATURE
```

### Database Rollback

If using migrations:

```bash
# Rollback database migration
npx prisma migrate reset
npx prisma migrate deploy --to <previous-migration>
```

## Monitoring and Alerting

### Key Metrics to Monitor

- **Response Times**: API endpoint performance
- **Error Rates**: 4xx and 5xx response rates
- **Feature Flag Usage**: Rollout effectiveness
- **Database Performance**: Query times and connection counts
- **Authentication Success**: Login/logout rates

### Recommended Alerts

- Response time > 5 seconds
- Error rate > 5%
- Database connection failures
- Authentication failures > 10%
- Rate limit exceeded frequently

### Log Analysis

Search for key patterns in logs:

```bash
# Error patterns
vercel logs --grep "ERROR"

# Performance issues
vercel logs --grep "processing_time_ms.*[5-9][0-9]{3}"

# Feature flag usage
vercel logs --grep "feature_flag"

# Authentication issues
vercel logs --grep "authentication.*failed"
```

## Troubleshooting

### Common Issues

#### 1. Environment Variables Not Loading

**Symptoms**: Features not working, authentication failing
**Solution**: 
```bash
# Check environment variables
vercel env ls
# Ensure variables are set for correct environment
vercel env add VARIABLE_NAME value --environment production
```

#### 2. Feature Flags Not Updating

**Symptoms**: New features not appearing
**Solution**:
```bash
# Clear Edge Config cache
vercel edge-config update <edge-config-id> --set cacheVersion=$(date +%s)
# Or restart the application
vercel redeploy --prod
```

#### 3. Database Connection Issues

**Symptoms**: 500 errors, database timeouts
**Solution**:
```bash
# Check database URL format
echo $DATABASE_URL
# Verify SSL requirements
# Check connection limits
```

#### 4. Authentication Redirects Failing

**Symptoms**: Login loops, redirect errors
**Solution**:
```bash
# Verify NEXTAUTH_URL matches deployment URL
vercel env get NEXTAUTH_URL
# Check provider configuration
# Verify callback URLs in OAuth provider
```

#### 5. Rate Limiting Too Aggressive

**Symptoms**: Legitimate requests being blocked
**Solution**:
```bash
# Increase rate limits temporarily
vercel env add RATE_LIMIT_HOUR 200
# Or disable rate limiting
vercel env add ENABLE_RATE_LIMITING false
```

### Debug Mode

Enable debug logging:

```bash
vercel env add LOG_LEVEL DEBUG
vercel env add DEBUG_MODE true
```

### Support Contacts

- **Technical Issues**: Create GitHub issue
- **Deployment Issues**: Check Vercel status page
- **Security Concerns**: Contact security team

## Performance Optimization

### Caching Strategy

- **Static Assets**: Cached by Vercel CDN
- **API Responses**: Cache-Control headers set based on content
- **Feature Flags**: Cached for 5 minutes
- **Database Queries**: Connection pooling enabled

### Optimization Tips

1. **Enable Edge Config**: Reduces feature flag lookup time
2. **Use Database Connection Pooling**: Improves database performance
3. **Monitor Bundle Size**: Keep JavaScript bundles small
4. **Optimize Images**: Use Next.js Image component
5. **Enable Compression**: Gzip/Brotli compression in Vercel

### Performance Monitoring

```bash
# Enable performance monitoring
vercel env add ENABLE_PERFORMANCE_MONITORING true

# Monitor key metrics
curl https://your-app.vercel.app/api/metrics
```

## Security Best Practices

### Environment Variables

- Never commit secrets to version control
- Use Vercel's encrypted environment variables
- Rotate secrets regularly
- Use different secrets for each environment

### Authentication

- Enable multi-factor authentication for admin accounts
- Use strong session secrets
- Implement proper session timeout
- Validate all user inputs

### Network Security

- Enable HTTPS only (enforced by Vercel)
- Configure proper CORS headers
- Implement rate limiting
- Use security headers (CSP, HSTS, etc.)

### Data Protection

- Hash sensitive data in logs
- Implement proper access controls
- Regular security audits
- Monitor for suspicious activity

---

For additional help, consult the [troubleshooting guide](./TROUBLESHOOTING.md) or create an issue in the project repository.