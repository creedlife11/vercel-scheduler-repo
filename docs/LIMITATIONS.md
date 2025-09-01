# System Limitations and Constraints

## Overview

This document outlines the known limitations, performance characteristics, scaling limits, and troubleshooting guidance for the Team Scheduler API. Understanding these constraints is essential for proper system integration and capacity planning.

## Table of Contents

- [Known Limitations](#known-limitations)
- [Performance Characteristics](#performance-characteristics)
- [Scaling Limits](#scaling-limits)
- [Resource Constraints](#resource-constraints)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Workarounds and Mitigation Strategies](#workarounds-and-mitigation-strategies)

## Known Limitations

### Scheduling Algorithm Constraints

#### Fixed Team Size
- **Limitation**: Exactly 6 engineers required for all schedules
- **Impact**: Cannot generate schedules for teams with different sizes
- **Rationale**: Algorithm is optimized for 6-person rotation patterns
- **Workaround**: Use placeholder names for smaller teams, or split larger teams

#### Sunday Start Requirement
- **Limitation**: All schedules must start on a Sunday
- **Impact**: Cannot generate schedules starting mid-week
- **Rationale**: Weekend coverage patterns assume Sunday-Saturday weeks
- **Workaround**: API auto-snaps to previous Sunday, or manually adjust start date

#### Maximum Schedule Length
- **Limitation**: Maximum 52 weeks per schedule generation
- **Impact**: Cannot generate multi-year schedules in single request
- **Rationale**: Memory and processing time constraints
- **Workaround**: Generate multiple schedules and concatenate results

### Data Format Limitations

#### Engineer Name Constraints
- **Character Set**: Only letters, spaces, hyphens, apostrophes, and periods allowed
- **Length**: Maximum 100 characters per name
- **Uniqueness**: Case-insensitive uniqueness required
- **Impact**: Cannot handle names with numbers, special characters, or emojis
- **Workaround**: Use normalized display names, maintain mapping to actual names

#### Leave Entry Limitations
- **Single Day Only**: Each leave entry represents one day
- **No Partial Days**: Cannot specify half-days or specific hours
- **No Recurring Leave**: Must specify each day individually
- **Impact**: Verbose for extended leave periods
- **Workaround**: Generate leave entries programmatically for date ranges

#### Export Format Constraints
- **CSV Encoding**: UTF-8 with BOM (may cause issues with some Excel versions)
- **XLSX Compatibility**: Requires Excel 2007+ or compatible software
- **JSON Size**: Large schedules may produce multi-MB JSON files
- **Impact**: Compatibility issues with older software
- **Workaround**: Use appropriate format for target system

### Authentication and Authorization

#### Session-Based Authentication
- **Limitation**: Requires web-based authentication flow
- **Impact**: Cannot use API keys or service-to-service authentication
- **Rationale**: Built on Auth.js/NextAuth framework
- **Workaround**: Implement headless browser automation for token acquisition

#### Role-Based Permissions
- **Limitation**: Fixed role hierarchy (Viewer < Editor < Admin)
- **Impact**: Cannot create custom permission sets
- **Rationale**: Simplified security model
- **Workaround**: Use Admin role for service accounts, implement app-level permissions

## Performance Characteristics

### Request Processing Times

| Operation | Typical Time | Maximum Time | Factors |
|-----------|--------------|--------------|---------|
| 4-week schedule (CSV) | 200-500ms | 2s | Engineer count, leave entries |
| 12-week schedule (XLSX) | 800ms-2s | 5s | Export complexity, server load |
| 52-week schedule (JSON) | 2-8s | 15s | Full fairness analysis |
| Health check | 10-50ms | 200ms | Cold start penalty |
| Artifact list | 100-300ms | 1s | Team artifact count |

### Memory Usage Patterns

```
Base Memory Usage: ~30-50MB (Python runtime + dependencies)
Per Schedule Generation:
- 4 weeks: +5-10MB
- 12 weeks: +15-25MB  
- 52 weeks: +50-100MB
Peak Memory: ~150-200MB (52-week XLSX generation)
```

### Cold Start Impact
- **Serverless Environment**: 1-3 second cold start penalty
- **Frequency**: Occurs after ~15 minutes of inactivity
- **Mitigation**: Health check endpoints can be used for warming

## Scaling Limits

### Request Rate Limits

| User Role | Requests/Hour | Burst Limit | Window |
|-----------|---------------|-------------|---------|
| Viewer | 50 | 10/minute | Rolling hour |
| Editor | 50 | 10/minute | Rolling hour |
| Admin | 200 | 20/minute | Rolling hour |
| Health endpoints | 1000 | 100/minute | Rolling hour |

### Concurrent Request Limits
- **Per User**: 3 concurrent schedule generations
- **System-wide**: 50 concurrent requests (Vercel limit)
- **Queue Behavior**: Requests queue with 30-second timeout

### Data Size Limits

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| Request body | 2MB | Server validation |
| Engineer names | 100 chars each | Pydantic validation |
| Leave entries | 1000 per request | Input validation |
| Response size | 50MB | Export manager |
| Artifact storage | 100MB per team | Team storage |

### Team and Artifact Limits

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Teams per user | 10 | UI/UX complexity |
| Artifacts per team | 500 | Storage costs |
| Artifact retention | 90 days | Compliance |
| Team name length | 50 characters | Database constraints |

## Resource Constraints

### Serverless Environment Limitations

#### Execution Time Limits
- **Maximum**: 15 seconds per request (Vercel limit)
- **Typical**: 95% of requests complete under 5 seconds
- **Timeout Behavior**: Request terminates, returns 504 error
- **Impact**: Very large schedules (52 weeks + complex leave) may timeout

#### Memory Constraints
- **Available**: 1GB RAM (Vercel Pro)
- **Typical Usage**: 50-200MB per request
- **OOM Behavior**: Process terminates, returns 500 error
- **Impact**: Multiple concurrent large schedule generations may fail

#### CPU Limitations
- **Shared Resources**: CPU time shared with other functions
- **Throttling**: May occur under high system load
- **Impact**: Increased processing times during peak usage

### Database and Storage

#### Artifact Storage
- **Backend**: Vercel Blob Storage or similar
- **Limitations**: No complex queries, eventual consistency
- **Performance**: 100-500ms for artifact operations
- **Reliability**: 99.9% availability SLA

#### Session Storage
- **Backend**: Database or Redis (implementation dependent)
- **Limitations**: Session timeout, concurrent session limits
- **Performance**: 10-100ms for auth operations

### External Dependencies

#### Python Package Dependencies
- **pandas**: Required for CSV/Excel operations
- **pydantic**: Required for validation
- **openpyxl**: Required for XLSX generation
- **Risk**: Package vulnerabilities, version conflicts
- **Mitigation**: Regular dependency updates, security scanning

#### Runtime Dependencies
- **Python 3.8+**: Minimum version requirement
- **Node.js 18+**: For Next.js frontend
- **Risk**: Runtime deprecation, security patches
- **Mitigation**: Regular runtime updates

## Troubleshooting Guide

### Common Issues and Solutions

#### Schedule Generation Failures

**Issue**: "Schedule generation constraint violation"
```json
{
  "error": "Schedule generation constraint violation",
  "details": [{"field": "schedule_constraints", "message": "Cannot assign oncall on weekend"}]
}
```
**Cause**: Scheduling algorithm cannot satisfy constraints with given inputs
**Solution**: 
- Reduce leave conflicts during critical periods
- Adjust rotation seeds to provide more flexibility
- Verify engineer availability patterns

**Issue**: "Request validation failed - Engineer names must be unique"
```json
{
  "error": "Request validation failed",
  "details": [{"field": "engineers", "message": "Duplicate engineer names detected"}]
}
```
**Cause**: Case-insensitive duplicate names in engineer list
**Solution**:
- Check for names that differ only in capitalization
- Look for extra whitespace or special characters
- Use name normalization before submission

#### Authentication Problems

**Issue**: "Authentication required"
**Cause**: Missing or invalid JWT token
**Solution**:
- Verify token is included in Authorization header
- Check token expiration and refresh if needed
- Ensure proper Bearer format: `Bearer <token>`

**Issue**: "Insufficient permissions"
**Cause**: User role lacks required permissions
**Solution**:
- Verify user has Editor/Admin role for schedule generation
- Check team membership for artifact access
- Contact admin to update user permissions

#### Performance Issues

**Issue**: Request timeouts (504 errors)
**Cause**: Processing time exceeds 15-second limit
**Solution**:
- Reduce schedule length (use fewer weeks)
- Minimize leave entries during generation
- Retry during off-peak hours
- Consider breaking large schedules into smaller chunks

**Issue**: Rate limit exceeded (429 errors)
**Cause**: Too many requests in time window
**Solution**:
- Implement exponential backoff retry logic
- Cache results to reduce API calls
- Upgrade to Admin role for higher limits
- Distribute requests across multiple users

#### Export Format Issues

**Issue**: CSV encoding problems in Excel
**Cause**: UTF-8 BOM handling varies by Excel version
**Solution**:
- Use "Data > From Text" import in Excel
- Try XLSX format instead of CSV
- Use UTF-8 compatible text editor first

**Issue**: XLSX file corruption
**Cause**: Large file size or memory constraints
**Solution**:
- Reduce schedule length
- Use CSV format for large schedules
- Retry generation during low-load periods

### Debugging Steps

#### 1. Check Request ID
Every error response includes a `request_id`. Use this for:
- Correlating logs across systems
- Support ticket references
- Debugging specific request flows

#### 2. Validate Input Data
```bash
# Test with minimal valid input
curl -X POST /api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engineers": ["A", "B", "C", "D", "E", "F"],
    "start_sunday": "2025-01-05",
    "weeks": 1,
    "format": "csv"
  }'
```

#### 3. Check System Health
```bash
# Verify service health
curl /api/healthz

# Check dependencies
curl /api/readyz
```

#### 4. Monitor Rate Limits
Check response headers:
- `X-RateLimit-Remaining`: Requests left
- `X-RateLimit-Reset`: When limit resets
- `Retry-After`: Wait time for 429 errors

#### 5. Test Authentication
```bash
# Verify token validity
curl -H "Authorization: Bearer $TOKEN" /api/artifacts/list
```

### Performance Monitoring

#### Key Metrics to Track
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Rate limit hit rates
- Memory usage patterns
- Cold start frequency

#### Alerting Thresholds
- Error rate > 5% over 5 minutes
- P95 latency > 10 seconds
- Rate limit hits > 10% of requests
- Cold starts > 50% of requests

## Workarounds and Mitigation Strategies

### Handling Large Teams

**Problem**: Need to schedule more than 6 engineers
**Solutions**:
1. **Split Team Approach**: Divide into multiple 6-person sub-teams
2. **Rotation Groups**: Create overlapping rotation groups
3. **Placeholder Strategy**: Use placeholder names, map to actual engineers

```python
# Example: Split large team
def split_team(engineers, group_size=6):
    groups = []
    for i in range(0, len(engineers), group_size):
        group = engineers[i:i+group_size]
        # Pad with placeholders if needed
        while len(group) < group_size:
            group.append(f"Placeholder_{len(group)}")
        groups.append(group)
    return groups
```

### Extended Leave Handling

**Problem**: Multi-week leave periods are verbose to specify
**Solution**: Generate leave entries programmatically

```python
from datetime import date, timedelta

def generate_leave_range(engineer, start_date, end_date, reason="Leave"):
    """Generate leave entries for a date range."""
    current = start_date
    entries = []
    
    while current <= end_date:
        # Skip weekends if desired
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            entries.append({
                "engineer": engineer,
                "date": current.isoformat(),
                "reason": reason
            })
        current += timedelta(days=1)
    
    return entries

# Usage
vacation_leave = generate_leave_range(
    "Alice Johnson",
    date(2025, 1, 15),
    date(2025, 1, 25),
    "Vacation"
)
```

### Multi-Year Scheduling

**Problem**: Cannot generate schedules longer than 52 weeks
**Solution**: Chain multiple schedule generations

```python
def generate_multi_year_schedule(engineers, start_date, total_weeks):
    """Generate multi-year schedule by chaining requests."""
    schedules = []
    current_start = start_date
    remaining_weeks = total_weeks
    
    while remaining_weeks > 0:
        chunk_weeks = min(remaining_weeks, 52)
        
        schedule = generate_schedule(
            engineers=engineers,
            start_sunday=current_start,
            weeks=chunk_weeks,
            format="json"
        )
        
        schedules.append(schedule)
        
        # Calculate next start date
        current_start += timedelta(weeks=chunk_weeks)
        remaining_weeks -= chunk_weeks
    
    return merge_schedules(schedules)
```

### High-Availability Patterns

**Problem**: Serverless cold starts and timeouts
**Solutions**:

1. **Warming Strategy**:
```javascript
// Keep functions warm with periodic health checks
setInterval(() => {
    fetch('/api/healthz').catch(() => {});
}, 10 * 60 * 1000); // Every 10 minutes
```

2. **Retry with Backoff**:
```javascript
async function retryWithBackoff(fn, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            
            const delay = Math.min(1000 * Math.pow(2, i), 10000);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}
```

3. **Circuit Breaker Pattern**:
```javascript
class CircuitBreaker {
    constructor(threshold = 5, timeout = 60000) {
        this.threshold = threshold;
        this.timeout = timeout;
        this.failures = 0;
        this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
        this.nextAttempt = Date.now();
    }
    
    async call(fn) {
        if (this.state === 'OPEN') {
            if (Date.now() < this.nextAttempt) {
                throw new Error('Circuit breaker is OPEN');
            }
            this.state = 'HALF_OPEN';
        }
        
        try {
            const result = await fn();
            this.onSuccess();
            return result;
        } catch (error) {
            this.onFailure();
            throw error;
        }
    }
    
    onSuccess() {
        this.failures = 0;
        this.state = 'CLOSED';
    }
    
    onFailure() {
        this.failures++;
        if (this.failures >= this.threshold) {
            this.state = 'OPEN';
            this.nextAttempt = Date.now() + this.timeout;
        }
    }
}
```

### Caching Strategies

**Problem**: Repeated requests for similar schedules
**Solution**: Implement intelligent caching

```javascript
class ScheduleCache {
    constructor(ttl = 3600000) { // 1 hour TTL
        this.cache = new Map();
        this.ttl = ttl;
    }
    
    generateKey(request) {
        // Create cache key from request parameters
        const { engineers, start_sunday, weeks, seeds, leave } = request;
        return JSON.stringify({
            engineers: engineers.sort(),
            start_sunday,
            weeks,
            seeds,
            leave: leave.sort((a, b) => a.date.localeCompare(b.date))
        });
    }
    
    get(request) {
        const key = this.generateKey(request);
        const cached = this.cache.get(key);
        
        if (cached && Date.now() - cached.timestamp < this.ttl) {
            return cached.data;
        }
        
        return null;
    }
    
    set(request, data) {
        const key = this.generateKey(request);
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }
}
```

This comprehensive documentation of limitations and constraints helps users understand system boundaries and implement appropriate workarounds for their specific use cases.