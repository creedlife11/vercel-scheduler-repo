import time
import json
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class RateLimitInfo:
    requests: int
    window_start: float
    last_request: float

class RateLimitExceeded(Exception):
    def __init__(self, message: str, retry_after: int):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)

class RateLimiter:
    """Simple in-memory rate limiter with sliding window."""
    
    def __init__(self):
        self.limits: Dict[str, RateLimitInfo] = {}
        self.cleanup_interval = 3600  # Clean up old entries every hour
        self.last_cleanup = time.time()
    
    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limit.
        Returns (allowed, headers) tuple.
        """
        current_time = time.time()
        
        # Periodic cleanup of old entries
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
        
        # Get or create rate limit info for this key
        if key not in self.limits:
            self.limits[key] = RateLimitInfo(
                requests=0,
                window_start=current_time,
                last_request=current_time
            )
        
        limit_info = self.limits[key]
        
        # Check if we need to reset the window
        if current_time - limit_info.window_start >= window_seconds:
            limit_info.requests = 0
            limit_info.window_start = current_time
        
        # Check if limit exceeded
        if limit_info.requests >= max_requests:
            retry_after = int(window_seconds - (current_time - limit_info.window_start)) + 1
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(limit_info.window_start + window_seconds)),
                "Retry-After": str(retry_after)
            }
            return False, headers
        
        # Update counters
        limit_info.requests += 1
        limit_info.last_request = current_time
        
        # Return success with rate limit headers
        remaining = max_requests - limit_info.requests
        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(limit_info.window_start + window_seconds))
        }
        
        return True, headers
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove entries that haven't been used in the last hour."""
        cutoff_time = current_time - 3600  # 1 hour ago
        
        keys_to_remove = [
            key for key, info in self.limits.items()
            if info.last_request < cutoff_time
        ]
        
        for key in keys_to_remove:
            del self.limits[key]
        
        self.last_cleanup = current_time

# Global rate limiter instance
rate_limiter = RateLimiter()

def get_rate_limit_key(request, user_id: Optional[str] = None) -> str:
    """Generate rate limit key based on user ID or IP."""
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP-based limiting
    ip = get_client_ip(request)
    return f"ip:{ip}"

def get_client_ip(request) -> str:
    """Extract client IP from request."""
    if not request or not hasattr(request, 'headers'):
        return 'unknown'
    
    headers = request.headers
    
    # Check various headers for the real IP
    for header in ['x-forwarded-for', 'x-real-ip', 'cf-connecting-ip']:
        if header in headers:
            ip = headers[header]
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            return ip
    
    return getattr(request, 'remote_addr', 'unknown')

def check_request_limits(request, user_id: Optional[str] = None, 
                        max_requests: int = 100, window_seconds: int = 3600) -> Dict[str, str]:
    """
    Check rate limits and return headers.
    Raises RateLimitExceeded if limit exceeded.
    """
    key = get_rate_limit_key(request, user_id)
    allowed, headers = rate_limiter.check_rate_limit(key, max_requests, window_seconds)
    
    if not allowed:
        retry_after = int(headers.get("Retry-After", "60"))
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {retry_after} seconds.",
            retry_after
        )
    
    return headers

def validate_request_size(request, max_size_mb: float = 1.0):
    """Validate request body size."""
    if not hasattr(request, 'body'):
        return
    
    body = request.body
    if isinstance(body, (bytes, bytearray)):
        size_bytes = len(body)
    elif isinstance(body, str):
        size_bytes = len(body.encode('utf-8'))
    else:
        return  # Can't determine size
    
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    
    if size_bytes > max_size_bytes:
        raise ValueError(f"Request body too large: {size_bytes} bytes (max: {max_size_bytes} bytes)")

def validate_input_limits(data: dict):
    """Validate input parameters are within safe limits."""
    errors = []
    
    # Check engineer count
    engineers = data.get('engineers', [])
    if isinstance(engineers, list) and len(engineers) > 20:
        errors.append("Too many engineers (max: 20)")
    
    # Check weeks count
    weeks = data.get('weeks', 0)
    if isinstance(weeks, (int, float)) and weeks > 52:
        errors.append("Too many weeks (max: 52)")
    
    # Check leave entries
    leave = data.get('leave', [])
    if isinstance(leave, list) and len(leave) > 1000:
        errors.append("Too many leave entries (max: 1000)")
    
    # Check engineer name lengths
    if isinstance(engineers, list):
        for i, engineer in enumerate(engineers):
            if isinstance(engineer, str) and len(engineer) > 100:
                errors.append(f"Engineer name {i+1} too long (max: 100 characters)")
    
    if errors:
        raise ValueError("; ".join(errors))

def sanitize_input_data(data: dict) -> dict:
    """Sanitize input data to prevent injection attacks."""
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Basic string sanitization
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_string(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input_data(value)
        else:
            sanitized[key] = value
    
    return sanitized

def sanitize_string(s: str) -> str:
    """Basic string sanitization."""
    if not isinstance(s, str):
        return s
    
    # Remove null bytes and control characters (except newlines and tabs)
    sanitized = ''.join(char for char in s if ord(char) >= 32 or char in '\n\t')
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
    
    return sanitized.strip()

# Security headers for responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
}

def add_security_headers(headers: dict) -> dict:
    """Add security headers to response."""
    return {**headers, **SECURITY_HEADERS}