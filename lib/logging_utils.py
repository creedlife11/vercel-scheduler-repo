"""
Structured logging utilities for the scheduler application.
Provides request tracking, performance monitoring, and structured log entries.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import sys


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class RequestMetrics:
    """Metrics collected during request processing."""
    request_id: str
    start_time: datetime
    input_size: int
    engineer_count: int
    weeks: int
    processing_time_ms: Optional[int] = None
    export_format: str = "csv"
    cache_hit: bool = False
    output_size: Optional[int] = None
    memory_usage_mb: Optional[float] = None


@dataclass
class LogEntry:
    """Structured log entry with consistent format."""
    timestamp: datetime
    level: LogLevel
    message: str
    request_id: str
    component: str
    metrics: Optional[RequestMetrics] = None
    error_details: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted log entries.
    Tracks request lifecycle and performance metrics.
    """
    
    def __init__(self, component: str = "scheduler"):
        self.component = component
        self._active_requests: Dict[str, RequestMetrics] = {}
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID for tracking."""
        return str(uuid.uuid4())[:8]
    
    def start_request(self, request_id: str, input_data: Dict[str, Any]) -> RequestMetrics:
        """Start tracking a new request."""
        metrics = RequestMetrics(
            request_id=request_id,
            start_time=datetime.utcnow(),
            input_size=len(json.dumps(input_data, default=str)),
            engineer_count=len(input_data.get("engineers", [])),
            weeks=input_data.get("weeks", 0),
            export_format=input_data.get("format", "csv")
        )
        self._active_requests[request_id] = metrics
        
        self._log(LogLevel.INFO, f"Request started", request_id, metrics=metrics)
        return metrics
    
    def end_request(self, request_id: str, success: bool = True, output_size: Optional[int] = None) -> Optional[RequestMetrics]:
        """End request tracking and log final metrics."""
        if request_id not in self._active_requests:
            self._log(LogLevel.WARNING, f"Attempted to end unknown request", request_id)
            return None
        
        metrics = self._active_requests[request_id]
        end_time = datetime.utcnow()
        metrics.processing_time_ms = int((end_time - metrics.start_time).total_seconds() * 1000)
        metrics.output_size = output_size
        
        # Try to get memory usage (basic implementation)
        try:
            import psutil
            process = psutil.Process()
            metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        except ImportError:
            # psutil not available, skip memory tracking
            pass
        except Exception:
            # Any other error, skip memory tracking
            pass
        
        status = "completed" if success else "failed"
        self._log(LogLevel.INFO, f"Request {status}", request_id, metrics=metrics)
        
        # Clean up
        del self._active_requests[request_id]
        return metrics
    
    def log_validation_error(self, request_id: str, field: str, message: str, value: Any = None):
        """Log validation errors with structured details."""
        error_details = {
            "field": field,
            "message": message,
            "value": str(value) if value is not None else None
        }
        self._log(LogLevel.WARNING, f"Validation error in field '{field}'", request_id, error_details=error_details)
    
    def log_schedule_generation(self, request_id: str, engineers: List[str], weeks: int, leave_count: int):
        """Log schedule generation details."""
        extra_data = {
            "engineers": [self._hash_name(name) for name in engineers],  # Hash for privacy
            "weeks": weeks,
            "leave_entries": leave_count
        }
        self._log(LogLevel.INFO, "Starting schedule generation", request_id, extra_data=extra_data)
    
    def log_export_generation(self, request_id: str, format_type: str, size_bytes: int):
        """Log export generation details."""
        extra_data = {
            "format": format_type,
            "size_bytes": size_bytes
        }
        self._log(LogLevel.INFO, f"Generated {format_type.upper()} export", request_id, extra_data=extra_data)
    
    def log_error(self, request_id: str, error: Exception, context: str = ""):
        """Log errors with full context."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        self._log(LogLevel.ERROR, f"Error occurred: {context}", request_id, error_details=error_details)
    
    def log_invariant_violation(self, request_id: str, violation_type: str, details: Dict[str, Any]):
        """Log scheduling invariant violations."""
        error_details = {
            "violation_type": violation_type,
            "details": details
        }
        self._log(LogLevel.ERROR, f"Invariant violation: {violation_type}", request_id, error_details=error_details)
    
    def _log(self, level: LogLevel, message: str, request_id: str, 
             metrics: Optional[RequestMetrics] = None, 
             error_details: Optional[Dict[str, Any]] = None,
             extra_data: Optional[Dict[str, Any]] = None):
        """Internal method to output structured log entries."""
        
        # Get metrics from active requests if not provided
        if metrics is None and request_id in self._active_requests:
            metrics = self._active_requests[request_id]
        
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            request_id=request_id,
            component=self.component,
            metrics=metrics,
            error_details=error_details,
            extra_data=extra_data
        )
        
        # Convert to JSON and output
        log_dict = asdict(entry)
        # Convert datetime objects to ISO strings
        log_dict["timestamp"] = entry.timestamp.isoformat() + "Z"
        if metrics:
            log_dict["metrics"]["start_time"] = metrics.start_time.isoformat() + "Z"
        
        # Remove None values to keep logs clean
        log_dict = self._remove_none_values(log_dict)
        
        # Output to stderr for structured logging
        print(json.dumps(log_dict, default=str), file=sys.stderr)
    
    def _hash_name(self, name: str) -> str:
        """Hash engineer names for privacy in logs."""
        import hashlib
        return hashlib.sha256(name.encode()).hexdigest()[:8]
    
    def _remove_none_values(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively remove None values from dictionary."""
        if isinstance(d, dict):
            return {k: self._remove_none_values(v) for k, v in d.items() if v is not None}
        elif isinstance(d, list):
            return [self._remove_none_values(item) for item in d if item is not None]
        else:
            return d


# Global logger instance
logger = StructuredLogger("scheduler-api")