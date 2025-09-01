"""
Optional metrics endpoint for performance monitoring.
Provides basic system and application metrics.
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any
from lib.rate_limiter import check_request_limits, add_security_headers, RateLimitExceeded
from lib.auth_middleware import require_role, AuthenticationError, AuthorizationError


def handler(request):
    """Metrics endpoint for performance monitoring."""
    
    if request.method != "GET":
        headers = add_security_headers({"Content-Type": "application/json"})
        return (405, json.dumps({"error": "Method not allowed"}), headers)
    
    # Check if metrics are enabled (could be controlled by environment variable)
    metrics_enabled = os.environ.get("ENABLE_METRICS", "false").lower() == "true"
    
    if not metrics_enabled:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (404, json.dumps({"error": "Metrics endpoint not enabled"}), headers)
    
    # Authentication required for metrics (ADMIN only)
    try:
        user = require_role(request, ["ADMIN"])
    except AuthenticationError:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (401, json.dumps({"error": "Authentication required"}), headers)
    except AuthorizationError:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (403, json.dumps({"error": "Admin access required"}), headers)
    except Exception:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (500, json.dumps({"error": "Authentication check failed"}), headers)
    
    # Rate limiting for metrics (restrictive)
    try:
        rate_limit_headers = check_request_limits(request, user.id, max_requests=100, window_seconds=3600)
    except RateLimitExceeded as e:
        headers = add_security_headers({"Content-Type": "application/json", "Retry-After": str(e.retry_after)})
        return (429, json.dumps({"error": "Rate limit exceeded"}), headers)
    except Exception:
        rate_limit_headers = {}  # Continue without rate limiting if check fails
    
    metrics_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "scheduler-api",
        "version": "2.0",
        "system": _get_system_metrics(),
        "application": _get_application_metrics()
    }
    
    headers = {
        "Content-Type": "application/json",
        **rate_limit_headers
    }
    headers = add_security_headers(headers)
    
    return (200, json.dumps(metrics_data), headers)


def _get_system_metrics() -> Dict[str, Any]:
    """Get basic system metrics."""
    metrics = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform
    }
    
    # Try to get memory info if psutil is available
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        metrics.update({
            "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "memory_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads()
        })
    except ImportError:
        metrics["memory_info"] = "psutil not available"
    except Exception as e:
        metrics["memory_info"] = f"Error getting memory info: {str(e)}"
    
    return metrics


def _get_application_metrics() -> Dict[str, Any]:
    """Get application-specific metrics."""
    
    # Basic application metrics
    metrics = {
        "uptime_info": "Process uptime not tracked in serverless",
        "environment": os.environ.get("VERCEL_ENV", "unknown")
    }
    
    # Could add more application-specific metrics here:
    # - Request counts (would need persistent storage)
    # - Average processing times (would need persistent storage)
    # - Error rates (would need persistent storage)
    
    return metrics