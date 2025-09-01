# Operations Runbook

This runbook provides operational procedures for maintaining and monitoring the Enhanced Team Scheduler application in production.

## Table of Contents

- [Daily Operations](#daily-operations)
- [Monitoring Procedures](#monitoring-procedures)
- [Incident Response](#incident-response)
- [Maintenance Tasks](#maintenance-tasks)
- [Performance Optimization](#performance-optimization)
- [Security Operations](#security-operations)
- [Backup and Recovery](#backup-and-recovery)
- [Capacity Planning](#capacity-planning)

## Daily Operations

### Morning Health Check (5 minutes)

```bash
#!/bin/bash
# daily-health-check.sh

echo "🌅 Daily Health Check - $(date)"
echo "=================================="

# 1. Basic health check
echo "1. Health Check:"
health_status=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/healthz)
if [ $health_status -eq 200 ]; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed (HTTP $health_status)"
fi

# 2. Readiness check
echo "2. Readiness Check:"
ready_status=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/readyz)
if [ $ready_status -eq 200 ]; then
    echo "   ✅ Readiness check passed"
else
    echo "   ❌ Readiness check failed (HTTP $ready_status)"
fi

# 3. Feature flags check
echo "3. Feature Flags:"
features_status=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/config/features)
if [ $features_status -eq 200 ]; then
    echo "   ✅ Feature flags accessible"
else
    echo "   ❌ Feature flags failed (HTTP $features_status)"
fi

# 4. Check recent errors
echo "4. Recent Errors (last 24h):"
error_count=$(vercel logs --since 24h --grep "ERROR" | wc -l)
echo "   📊 Error count: $error_count"
if [ $error_count -gt 100 ]; then
    echo "   ⚠️  High error rate detected"
fi

# 5. Performance check
echo "5. Performance Check:"
response_time=$(curl -w "%{time_total}" -s -o /dev/null https://your-app.vercel.app/api/healthz)
echo "   ⏱️  Response time: ${response_time}s"
if (( $(echo "$response_time > 2.0" | bc -l) )); then
    echo "   ⚠️  Slow response time"
fi

echo "=================================="
echo "Daily health check complete"
```

### Weekly Review (30 minutes)

```bash
#!/bin/bash
# weekly-review.sh

echo "📊 Weekly Review - $(date)"
echo "========================="

# 1. Performance metrics
echo "1. Performance Metrics (last 7 days):"
vercel logs --since 7d --grep "processing_time_ms" | \
  grep -o "processing_time_ms\":[0-9]*" | \
  cut -d: -f2 | \
  awk '{sum+=$1; count++} END {print "   Average response time: " sum/count "ms"}'

# 2. Error analysis
echo "2. Error Analysis:"
echo "   Top error types:"
vercel logs --since 7d --grep "ERROR" | \
  grep -o "\"error\":\"[^\"]*\"" | \
  sort | uniq -c | sort -nr | head -5

# 3. Feature flag usage
echo "3. Feature Flag Usage:"
vercel logs --since 7d --grep "feature_flag" | \
  grep -o "\"flag\":\"[^\"]*\"" | \
  sort | uniq -c | sort -nr | head -10

# 4. User activity
echo "4. User Activity:"
request_count=$(vercel logs --since 7d --grep "request_id" | wc -l)
echo "   Total requests: $request_count"
echo "   Average per day: $((request_count / 7))"

# 5. Database performance (if applicable)
echo "5. Database Performance:"
vercel logs --since 7d --grep "database.*time" | \
  grep -o "time\":[0-9]*" | \
  cut -d: -f2 | \
  awk '{sum+=$1; count++} END {print "   Average DB query time: " sum/count "ms"}'
```

## Monitoring Procedures

### Key Metrics to Monitor

#### Application Metrics
- **Response Time**: < 2 seconds for 95th percentile
- **Error Rate**: < 1% of total requests
- **Availability**: > 99.9% uptime
- **Throughput**: Requests per minute/hour

#### System Metrics
- **Function Duration**: < 25 seconds (Vercel limit: 30s)
- **Memory Usage**: < 80% of allocated memory
- **Database Connections**: < 80% of connection pool
- **Feature Flag Response**: < 100ms

### Monitoring Commands

```bash
# Real-time monitoring
watch -n 30 'curl -s https://your-app.vercel.app/api/healthz && echo " - $(date)"'

# Performance monitoring
curl -w "@curl-format.txt" -s -o /dev/null https://your-app.vercel.app/api/generate

# Error rate monitoring
vercel logs --since 1h --grep "ERROR" | wc -l

# Feature flag monitoring
curl -s https://your-app.vercel.app/api/config/features | jq '.features | to_entries[] | select(.value.enabled == false)'
```

### Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Response Time | > 2s | > 5s | Investigate performance |
| Error Rate | > 1% | > 5% | Check logs, consider rollback |
| Availability | < 99% | < 95% | Immediate investigation |
| Memory Usage | > 80% | > 95% | Scale up or optimize |
| DB Connections | > 80% | > 95% | Check connection leaks |

## Incident Response

### Severity Levels

#### Severity 1 (Critical)
- Application completely down
- Data loss or corruption
- Security breach
- **Response Time**: 15 minutes
- **Resolution Time**: 2 hours

#### Severity 2 (High)
- Major feature not working
- Performance severely degraded
- Authentication issues
- **Response Time**: 30 minutes
- **Resolution Time**: 4 hours

#### Severity 3 (Medium)
- Minor feature issues
- Moderate performance impact
- Non-critical errors
- **Response Time**: 2 hours
- **Resolution Time**: 24 hours

### Incident Response Procedures

#### 1. Initial Response (First 15 minutes)

```bash
# Incident response checklist
echo "🚨 INCIDENT RESPONSE STARTED - $(date)"

# 1. Assess severity
curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/healthz
curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/readyz

# 2. Check recent deployments
vercel ls --limit 5

# 3. Review recent logs
vercel logs --since 1h --grep "ERROR" | head -20

# 4. Check Vercel status
curl -s https://www.vercel-status.com/api/v2/status.json | jq '.status.indicator'

# 5. Notify team (if Severity 1 or 2)
# Send alert to incident channel
```

#### 2. Investigation (Next 30 minutes)

```bash
# Deep investigation
echo "🔍 INVESTIGATION PHASE"

# Check specific error patterns
vercel logs --since 2h --grep "500|502|503|504"

# Analyze performance
vercel logs --since 2h --grep "processing_time_ms.*[5-9][0-9]{3}"

# Check feature flag issues
curl -s https://your-app.vercel.app/api/config/features | jq '.error // empty'

# Database connectivity
vercel logs --since 2h --grep "database.*error"

# Authentication issues
vercel logs --since 2h --grep "authentication.*failed"
```

#### 3. Mitigation Options

```bash
# Quick mitigation options

# Option 1: Rollback to previous deployment
vercel rollback <previous-deployment-url>

# Option 2: Disable problematic feature
vercel env add ENABLE_PROBLEMATIC_FEATURE false

# Option 3: Increase resource limits
vercel env add RATE_LIMIT_HOUR 200
vercel env add MAX_REQUEST_SIZE_MB 5.0

# Option 4: Emergency maintenance mode
vercel env add MAINTENANCE_MODE true

# Option 5: Scale down to reduce load
vercel env add MAX_WEEKS_ALLOWED 26
```

### Post-Incident Review

After resolving an incident, conduct a post-mortem:

1. **Timeline**: Document incident timeline
2. **Root Cause**: Identify underlying cause
3. **Impact**: Assess user and business impact
4. **Response**: Evaluate response effectiveness
5. **Action Items**: Create prevention tasks

## Maintenance Tasks

### Weekly Maintenance (1 hour)

```bash
#!/bin/bash
# weekly-maintenance.sh

echo "🔧 Weekly Maintenance - $(date)"

# 1. Update dependencies (in development)
npm audit
npm update

# 2. Clean up old logs (if applicable)
# Vercel handles log retention automatically

# 3. Review and rotate secrets
echo "Review secret rotation schedule:"
echo "- NEXTAUTH_SECRET: Last rotated $(vercel env get NEXTAUTH_SECRET_ROTATED || echo 'Never')"
echo "- Database passwords: Check with DBA team"

# 4. Update feature flag documentation
npm run deploy:config > current-config.json
echo "Current configuration saved to current-config.json"

# 5. Performance optimization review
echo "Performance review:"
vercel logs --since 7d --grep "processing_time_ms" | \
  grep -o "processing_time_ms\":[0-9]*" | \
  cut -d: -f2 | sort -n | tail -10
```

### Monthly Maintenance (2 hours)

```bash
#!/bin/bash
# monthly-maintenance.sh

echo "🗓️ Monthly Maintenance - $(date)"

# 1. Security review
echo "1. Security Review:"
echo "   - Review access logs"
echo "   - Check for suspicious activity"
echo "   - Verify SSL certificates"
echo "   - Review user permissions"

# 2. Performance analysis
echo "2. Performance Analysis:"
echo "   - Analyze 30-day performance trends"
echo "   - Identify optimization opportunities"
echo "   - Review database performance"

# 3. Capacity planning
echo "3. Capacity Planning:"
echo "   - Review usage growth"
echo "   - Plan for scaling needs"
echo "   - Update resource allocations"

# 4. Backup verification
echo "4. Backup Verification:"
echo "   - Test backup restoration"
echo "   - Verify backup integrity"
echo "   - Update backup procedures"

# 5. Documentation updates
echo "5. Documentation Updates:"
echo "   - Update runbooks"
echo "   - Review troubleshooting guides"
echo "   - Update deployment procedures"
```

## Performance Optimization

### Performance Monitoring

```bash
# Monitor key performance indicators
#!/bin/bash

# API response times
curl -w "Response time: %{time_total}s\n" -s -o /dev/null https://your-app.vercel.app/api/generate

# Database query performance
vercel logs --since 1h --grep "database.*time" | \
  grep -o "time\":[0-9]*" | \
  awk -F: '{sum+=$2; count++} END {print "Average DB time: " sum/count "ms"}'

# Memory usage trends
vercel logs --since 1h --grep "memory_usage_mb" | \
  grep -o "memory_usage_mb\":[0-9.]*" | \
  cut -d: -f2 | sort -n | tail -5
```

### Optimization Strategies

1. **Code Optimization**:
   ```bash
   # Enable performance monitoring
   vercel env add ENABLE_PERFORMANCE_MONITORING true
   
   # Profile slow operations
   vercel logs --grep "processing_time_ms.*[5-9][0-9]{3}"
   ```

2. **Database Optimization**:
   ```bash
   # Monitor connection usage
   vercel logs --grep "database.*connections"
   
   # Optimize query performance
   # Add indexes for frequently queried fields
   ```

3. **Caching Optimization**:
   ```bash
   # Enable feature flag caching
   vercel env add FEATURE_FLAG_CACHE_TTL 300
   
   # Cache static responses
   # Use CDN for static assets
   ```

## Security Operations

### Security Monitoring

```bash
#!/bin/bash
# security-monitoring.sh

echo "🔒 Security Monitoring - $(date)"

# 1. Authentication failures
echo "1. Authentication Failures (last 24h):"
auth_failures=$(vercel logs --since 24h --grep "authentication.*failed" | wc -l)
echo "   Count: $auth_failures"
if [ $auth_failures -gt 50 ]; then
    echo "   ⚠️  High authentication failure rate"
fi

# 2. Rate limiting triggers
echo "2. Rate Limiting (last 24h):"
rate_limit_hits=$(vercel logs --since 24h --grep "rate.*limit.*exceeded" | wc -l)
echo "   Count: $rate_limit_hits"

# 3. Suspicious activity
echo "3. Suspicious Activity:"
vercel logs --since 24h --grep "suspicious\|attack\|injection" | head -5

# 4. SSL/TLS issues
echo "4. SSL/TLS Status:"
ssl_status=$(curl -s -I https://your-app.vercel.app | grep -i "strict-transport-security")
echo "   HSTS: ${ssl_status:-'Not found'}"
```

### Security Procedures

#### Daily Security Tasks
- Review authentication logs
- Monitor rate limiting effectiveness
- Check for suspicious IP addresses
- Verify SSL certificate status

#### Weekly Security Tasks
- Review user access permissions
- Update security headers
- Scan for vulnerabilities
- Review API usage patterns

#### Monthly Security Tasks
- Rotate secrets and API keys
- Security audit and penetration testing
- Review and update security policies
- Update security documentation

### Security Incident Response

```bash
# Security incident response
#!/bin/bash

echo "🚨 SECURITY INCIDENT RESPONSE"

# 1. Immediate containment
echo "1. Immediate Actions:"
echo "   - Block suspicious IPs"
echo "   - Disable compromised accounts"
echo "   - Enable maintenance mode if needed"

# 2. Investigation
echo "2. Investigation:"
echo "   - Collect logs and evidence"
echo "   - Identify attack vectors"
echo "   - Assess data exposure"

# 3. Mitigation
echo "3. Mitigation:"
echo "   - Patch vulnerabilities"
echo "   - Update security controls"
echo "   - Reset compromised credentials"

# 4. Recovery
echo "4. Recovery:"
echo "   - Restore from clean backups"
echo "   - Verify system integrity"
echo "   - Resume normal operations"
```

## Backup and Recovery

### Backup Procedures

```bash
#!/bin/bash
# backup-procedures.sh

echo "💾 Backup Procedures - $(date)"

# 1. Configuration backup
echo "1. Configuration Backup:"
vercel env ls > "backup-env-$(date +%Y%m%d).txt"
npm run deploy:config > "backup-config-$(date +%Y%m%d).json"

# 2. Database backup (if applicable)
echo "2. Database Backup:"
# pg_dump $DATABASE_URL > "backup-db-$(date +%Y%m%d).sql"

# 3. Code backup
echo "3. Code Backup:"
git archive --format=tar.gz --prefix=scheduler-backup-$(date +%Y%m%d)/ HEAD > "backup-code-$(date +%Y%m%d).tar.gz"

# 4. Feature flag backup
echo "4. Feature Flag Backup:"
if [ -n "$EDGE_CONFIG" ]; then
    vercel edge-config get $EDGE_CONFIG > "backup-features-$(date +%Y%m%d).json"
fi
```

### Recovery Procedures

```bash
#!/bin/bash
# recovery-procedures.sh

echo "🔄 Recovery Procedures"

# 1. Environment recovery
echo "1. Environment Recovery:"
echo "   - Restore environment variables from backup"
echo "   - Verify configuration integrity"

# 2. Database recovery
echo "2. Database Recovery:"
echo "   - Restore from latest backup"
echo "   - Verify data integrity"
echo "   - Run migration if needed"

# 3. Application recovery
echo "3. Application Recovery:"
echo "   - Deploy from known good commit"
echo "   - Restore feature flags"
echo "   - Verify functionality"

# 4. Verification
echo "4. Verification:"
echo "   - Run health checks"
echo "   - Test critical functionality"
echo "   - Monitor for issues"
```

## Capacity Planning

### Usage Monitoring

```bash
#!/bin/bash
# capacity-monitoring.sh

echo "📈 Capacity Monitoring - $(date)"

# 1. Request volume trends
echo "1. Request Volume (last 30 days):"
# Analyze request patterns
vercel logs --since 30d --grep "request_id" | \
  awk '{print $1}' | cut -d'T' -f1 | sort | uniq -c | \
  awk '{print $2 ": " $1 " requests"}'

# 2. Resource utilization
echo "2. Resource Utilization:"
vercel logs --since 7d --grep "memory_usage_mb" | \
  grep -o "memory_usage_mb\":[0-9.]*" | \
  cut -d: -f2 | sort -n | tail -10

# 3. Performance trends
echo "3. Performance Trends:"
vercel logs --since 7d --grep "processing_time_ms" | \
  grep -o "processing_time_ms\":[0-9]*" | \
  cut -d: -f2 | sort -n | tail -10

# 4. Feature usage
echo "4. Feature Usage:"
vercel logs --since 7d --grep "feature_flag" | \
  grep -o "\"flag\":\"[^\"]*\"" | \
  sort | uniq -c | sort -nr
```

### Scaling Decisions

#### When to Scale Up
- Response times consistently > 2 seconds
- Error rates > 1%
- Memory usage > 80%
- Database connections > 80%

#### Scaling Options
1. **Vertical Scaling**: Increase function memory/timeout
2. **Horizontal Scaling**: Vercel handles automatically
3. **Database Scaling**: Increase connection pool, add read replicas
4. **Caching**: Implement Redis or similar

### Capacity Planning Checklist

- [ ] Monitor usage trends monthly
- [ ] Review performance metrics
- [ ] Plan for seasonal variations
- [ ] Estimate growth projections
- [ ] Budget for scaling costs
- [ ] Test scaling procedures
- [ ] Update capacity documentation

---

This runbook should be reviewed and updated quarterly to ensure it remains current with operational needs and system changes.