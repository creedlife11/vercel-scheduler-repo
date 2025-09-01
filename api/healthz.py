"""
Basic health check endpoint for monitoring.
Returns 200 OK if the service is running.
"""

import json
from datetime import datetime
from lib.rate_limiter import check_request_limits, add_security_headers, RateLimitExceeded


def handler(request):
    """Basic health check endpoint."""
    
    if request.method != "GET":
        headers = add_security_headers({"Content-Type": "application/json"})
        return (405, json.dumps({"error": "Method not allowed"}), headers)
    
    # Rate limiting for health checks (more permissive)
    try:
        rate_limit_headers = check_request_limits(request, max_requests=1000, window_seconds=3600)
    except RateLimitExceeded as e:
        headers = add_security_headers({"Content-Type": "application/json", "Retry-After": str(e.retry_after)})
        return (429, json.dumps({"error": "Rate limit exceeded"}), headers)
    except Exception:
        rate_limit_headers = {}  # Continue without rate limiting if check fails
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "scheduler-api",
        "version": "2.0"
    }
    
    headers = {
        "Content-Type": "application/json",
        **rate_limit_headers
    }
    headers = add_security_headers(headers)
    
    return (200, json.dumps(health_data), headers)