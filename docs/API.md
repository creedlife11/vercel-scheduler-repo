# Team Scheduler API Documentation

## Overview

The Team Scheduler API provides comprehensive schedule generation with fairness analysis, decision logging, and multi-format exports. This document provides detailed endpoint documentation with curl examples, validation rules, error conditions, and integration guides.

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Schedule Generation](#schedule-generation)
  - [Health & Monitoring](#health--monitoring)
  - [Artifact Management](#artifact-management)
- [Integration Guide](#integration-guide)
- [Best Practices](#best-practices)

## Authentication

All endpoints except health checks require authentication via Auth.js/NextAuth. Include the JWT token in the Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

### User Roles

- **Viewer**: Read-only access to artifacts
- **Editor**: Can generate schedules and manage artifacts  
- **Admin**: Full access including metrics and system management

### Getting a Token

```bash
# Login via the web interface first, then extract token from session
curl -X POST https://your-scheduler.vercel.app/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

## Rate Limiting

Rate limits are enforced per user and role:

- **Editors**: 50 requests per hour
- **Admins**: 200 requests per hour
- **Health endpoints**: 1000 requests per hour
- **Metrics**: 100 requests per hour (Admin only)

Rate limit headers are included in responses:
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Error Handling

The API uses structured error responses with detailed field-level validation errors. All errors include a `request_id` for debugging.

### Error Response Format

```json
{
  "error": "High-level error message",
  "details": [
    {
      "field": "field_name",
      "message": "Detailed error message",
      "code": "error_code",
      "value": "invalid_value"
    }
  ],
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-01-09T10:30:00Z"
}
```

### Common Error Codes

- `400`: Bad request - Invalid input data
- `401`: Authentication required
- `403`: Insufficient permissions
- `413`: Request too large (>2MB)
- `422`: Validation error with detailed field errors
- `429`: Rate limit exceeded
- `500`: Internal server error

## Endpoints

### Schedule Generation

#### POST /api/generate

Generates a team schedule with fairness analysis and decision logging.

**Authentication**: Required (Editor or Admin role)

**Request Body**:
```json
{
  "engineers": ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eve Brown", "Frank Miller"],
  "start_sunday": "2025-01-05",
  "weeks": 4,
  "seeds": {
    "weekend": 0,
    "chat": 0,
    "oncall": 1,
    "appointments": 2,
    "early": 0
  },
  "leave": [
    {
      "engineer": "Alice Johnson",
      "date": "2025-01-15",
      "reason": "Vacation"
    }
  ],
  "format": "csv"
}
```

**Validation Rules**:
- Exactly 6 engineers required
- Engineer names must be unique (case-insensitive)
- Names can contain letters, spaces, hyphens, apostrophes, and periods
- Start date must be a Sunday
- Maximum 52 weeks allowed
- Leave entries must reference valid engineers
- Seeds must be integers 0-5

**curl Examples**:

```bash
# Basic CSV generation
curl -X POST https://your-scheduler.vercel.app/api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engineers": ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eve Brown", "Frank Miller"],
    "start_sunday": "2025-01-05",
    "weeks": 4,
    "format": "csv"
  }' \
  --output schedule.csv

# XLSX with leave entries
curl -X POST https://your-scheduler.vercel.app/api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engineers": ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eve Brown", "Frank Miller"],
    "start_sunday": "2025-01-05",
    "weeks": 8,
    "seeds": {"weekend": 1, "chat": 2, "oncall": 0, "appointments": 3, "early": 1},
    "leave": [
      {"engineer": "Alice Johnson", "date": "2025-01-15", "reason": "Vacation"},
      {"engineer": "Bob Smith", "date": "2025-01-22", "reason": "Conference"}
    ],
    "format": "xlsx"
  }' \
  --output schedule.xlsx

# JSON with full data
curl -X POST https://your-scheduler.vercel.app/api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engineers": ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eve Brown", "Frank Miller"],
    "start_sunday": "2025-01-05",
    "weeks": 6,
    "format": "json"
  }' \
  --output schedule.json
```

**Response Headers**:
- `X-Request-ID`: Unique request identifier
- `X-RateLimit-Remaining`: Requests remaining
- `Content-Type`: Varies by format
- `Content-Disposition`: Attachment with descriptive filename

**CSV Response Format**:
```csv
# Schema Version: 2.0
# Generated: 2025-01-09T10:30:00Z
# Configuration: default, 6 engineers, 4 weeks
Date,Day,WeekIndex,Early1,Early2,Chat,OnCall,Appointments,1) Alice Johnson,Status 1,Shift 1,2) Bob Smith,Status 2,Shift 2,3) Carol Davis,Status 3,Shift 3,4) David Wilson,Status 4,Shift 4,5) Eve Brown,Status 5,Shift 5,6) Frank Miller,Status 6,Shift 6
2025-01-05,Sun,0,,,,,,,OFF,,Bob Smith,WORK,Weekend,,,,,
```

**JSON Response Structure**:
```json
{
  "schemaVersion": "2.0",
  "metadata": {
    "generation_timestamp": "2025-01-09T10:30:00Z",
    "configuration": {...},
    "engineer_count": 6,
    "weeks": 4,
    "start_date": "2025-01-05",
    "end_date": "2025-02-01",
    "total_days": 28
  },
  "schedule": [...],
  "fairnessReport": {
    "engineer_stats": {...},
    "equity_score": 0.12,
    "max_min_deltas": {...}
  },
  "decisionLog": [...]
}
```

### Health & Monitoring

#### GET /api/healthz

Basic health check for load balancers and monitoring systems.

**Authentication**: Not required

```bash
curl https://your-scheduler.vercel.app/api/healthz
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-09T10:30:00Z",
  "service": "scheduler-api",
  "version": "2.0"
}
```

#### GET /api/readyz

Comprehensive readiness check with dependency validation.

**Authentication**: Not required

```bash
curl https://your-scheduler.vercel.app/api/readyz
```

**Response**:
```json
{
  "status": "ready",
  "timestamp": "2025-01-09T10:30:00Z",
  "service": "scheduler-api",
  "version": "2.0",
  "checks": {
    "dependencies": {
      "status": "pass",
      "available": ["pandas", "pydantic", "openpyxl"],
      "missing": [],
      "message": "All dependencies available"
    },
    "modules": {
      "status": "pass",
      "successful": ["schedule_core", "export_manager", "models", "lib.logging_utils"],
      "failed": [],
      "message": "All core modules available"
    },
    "python": {
      "status": "pass",
      "version": "3.11.0",
      "required": ">=3.8",
      "message": "Python 3.11.0 is compatible"
    }
  }
}
```

#### GET /api/metrics

Performance and system metrics for monitoring.

**Authentication**: Required (Admin role only)

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://your-scheduler.vercel.app/api/metrics
```

**Response**:
```json
{
  "timestamp": "2025-01-09T10:30:00Z",
  "service": "scheduler-api",
  "version": "2.0",
  "system": {
    "python_version": "3.11.0",
    "platform": "linux",
    "memory_rss_mb": 45.2,
    "memory_vms_mb": 128.7,
    "cpu_percent": 2.1,
    "num_threads": 8
  },
  "application": {
    "uptime_info": "Process uptime not tracked in serverless",
    "environment": "production"
  }
}
```

### Artifact Management

#### GET /api/artifacts/list

List stored schedule artifacts for the user's team.

**Authentication**: Required (Any role)

```bash
# List artifacts for default team
curl -H "Authorization: Bearer $TOKEN" \
  https://your-scheduler.vercel.app/api/artifacts/list

# List artifacts for specific team
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-scheduler.vercel.app/api/artifacts/list?team_id=team_789&limit=20"
```

**Response**:
```json
{
  "artifacts": [
    {
      "id": "art_123e4567-e89b-12d3-a456-426614174000",
      "filename": "schedule_2025-01-05_4weeks_default.csv",
      "format": "CSV",
      "size_bytes": 2048,
      "created_at": "2025-01-09T10:30:00Z",
      "created_by": "user_456",
      "metadata": {
        "engineer_count": 6,
        "weeks": 4,
        "leave_entries": 2
      }
    }
  ],
  "total": 1,
  "team_id": "team_789"
}
```

#### GET /api/artifacts/get/{artifact_id}

Download a specific schedule artifact.

**Authentication**: Required (Any role, team access required)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-scheduler.vercel.app/api/artifacts/get/art_123e4567-e89b-12d3-a456-426614174000?team_id=team_789" \
  --output downloaded_schedule.csv
```

#### DELETE /api/artifacts/delete/{artifact_id}

Delete a specific schedule artifact.

**Authentication**: Required (Editor or Admin role)

```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "https://your-scheduler.vercel.app/api/artifacts/delete/art_123e4567-e89b-12d3-a456-426614174000?team_id=team_789"
```

**Response**:
```json
{
  "success": true
}
```

## Integration Guide

### Basic Integration Steps

1. **Authentication Setup**
   - Implement Auth.js/NextAuth in your application
   - Obtain JWT tokens for API access
   - Handle token refresh and expiration

2. **Schedule Generation Workflow**
   ```javascript
   // Example JavaScript integration
   async function generateSchedule(scheduleData) {
     const response = await fetch('/api/generate', {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${token}`,
         'Content-Type': 'application/json'
       },
       body: JSON.stringify(scheduleData)
     });
     
     if (!response.ok) {
       const error = await response.json();
       throw new Error(`Schedule generation failed: ${error.error}`);
     }
     
     return response.blob(); // For CSV/XLSX
     // or response.json() for JSON format
   }
   ```

3. **Error Handling**
   ```javascript
   try {
     const schedule = await generateSchedule(data);
   } catch (error) {
     if (error.status === 422) {
       // Handle validation errors
       const errorData = await error.json();
       errorData.details.forEach(detail => {
         console.log(`Field ${detail.field}: ${detail.message}`);
       });
     }
   }
   ```

### Python Integration Example

```python
import requests
import json

class SchedulerClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def generate_schedule(self, engineers, start_sunday, weeks, **kwargs):
        data = {
            'engineers': engineers,
            'start_sunday': start_sunday,
            'weeks': weeks,
            **kwargs
        }
        
        response = requests.post(
            f'{self.base_url}/api/generate',
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 422:
            error_data = response.json()
            raise ValueError(f"Validation errors: {error_data['details']}")
        
        response.raise_for_status()
        return response.content
    
    def health_check(self):
        response = requests.get(f'{self.base_url}/api/healthz')
        return response.json()

# Usage
client = SchedulerClient('https://your-scheduler.vercel.app', token)
schedule_csv = client.generate_schedule(
    engineers=['Alice', 'Bob', 'Carol', 'David', 'Eve', 'Frank'],
    start_sunday='2025-01-05',
    weeks=4,
    format='csv'
)
```

### Webhook Integration

For automated schedule generation, you can integrate with external systems:

```javascript
// Example webhook handler
app.post('/webhook/schedule-request', async (req, res) => {
  const { team_id, engineers, start_date, weeks } = req.body;
  
  try {
    const schedule = await generateSchedule({
      engineers,
      start_sunday: start_date,
      weeks,
      format: 'json'
    });
    
    // Store or process the schedule
    await processSchedule(team_id, schedule);
    
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Best Practices

### Input Validation

1. **Engineer Names**
   - Trim whitespace before sending
   - Ensure names are unique (case-insensitive)
   - Use only letters, spaces, hyphens, apostrophes, and periods
   - Maximum 100 characters per name

2. **Date Handling**
   - Always use ISO 8601 format (YYYY-MM-DD)
   - Ensure start dates are Sundays
   - Validate leave dates are within schedule range

3. **Request Size**
   - Keep requests under 2MB
   - Limit leave entries to reasonable numbers
   - Use appropriate week counts (1-52)

### Error Handling

1. **Retry Logic**
   ```javascript
   async function retryRequest(fn, maxRetries = 3) {
     for (let i = 0; i < maxRetries; i++) {
       try {
         return await fn();
       } catch (error) {
         if (error.status === 429) {
           // Rate limited, wait and retry
           const retryAfter = error.headers['retry-after'] || 60;
           await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
           continue;
         }
         throw error;
       }
     }
   }
   ```

2. **Validation Error Handling**
   - Parse field-level errors from 422 responses
   - Display user-friendly error messages
   - Highlight problematic form fields

### Performance Optimization

1. **Caching**
   - Cache authentication tokens
   - Store frequently used team configurations
   - Cache artifact lists for short periods

2. **Request Optimization**
   - Use appropriate formats (CSV for simple exports, JSON for rich data)
   - Batch artifact operations when possible
   - Implement client-side validation to reduce server requests

### Security Considerations

1. **Token Management**
   - Store tokens securely (httpOnly cookies recommended)
   - Implement token refresh logic
   - Handle token expiration gracefully

2. **Input Sanitization**
   - Validate all inputs client-side
   - Don't trust client-side validation alone
   - Use HTTPS for all requests

3. **Rate Limiting**
   - Implement client-side rate limiting
   - Handle 429 responses appropriately
   - Monitor usage patterns

### Monitoring and Debugging

1. **Request Tracking**
   - Log request IDs for debugging
   - Monitor response times
   - Track error rates by endpoint

2. **Health Monitoring**
   - Regularly check /api/healthz
   - Monitor /api/readyz for dependency issues
   - Set up alerts for service degradation

3. **Logging**
   ```javascript
   // Example logging wrapper
   async function apiCall(endpoint, options) {
     const requestId = generateRequestId();
     console.log(`[${requestId}] Starting ${endpoint}`);
     
     try {
       const response = await fetch(endpoint, options);
       const responseRequestId = response.headers.get('X-Request-ID');
       console.log(`[${requestId}] Success: ${response.status}, Server ID: ${responseRequestId}`);
       return response;
     } catch (error) {
       console.error(`[${requestId}] Error: ${error.message}`);
       throw error;
     }
   }
   ```

This documentation provides comprehensive guidance for integrating with the Team Scheduler API. For additional support or questions, please refer to the request ID in error responses when contacting support.