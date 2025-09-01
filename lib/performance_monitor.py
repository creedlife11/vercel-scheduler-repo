"""
Performance monitoring utilities for tracking processing times, memory usage, and output sizes.
"""

import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics for a specific operation."""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    memory_start_mb: Optional[float] = None
    memory_end_mb: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    cpu_time_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class PerformanceMonitor:
    """
    Monitor performance metrics for various operations.
    Tracks timing, memory usage, and throughput.
    """
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self._active_operations: Dict[str, PerformanceMetrics] = {}
    
    @contextmanager
    def monitor_operation(self, operation_name: str, input_size: Optional[int] = None):
        """
        Context manager for monitoring an operation's performance.
        
        Usage:
            with monitor.monitor_operation("schedule_generation", input_size=1024) as metrics:
                # Do work here
                pass
            # metrics.duration_ms will be automatically set
        """
        metrics = self.start_operation(operation_name, input_size)
        try:
            yield metrics
            self.end_operation(operation_name, success=True)
        except Exception as e:
            self.end_operation(operation_name, success=False, error_message=str(e))
            raise
    
    def start_operation(self, operation_name: str, input_size: Optional[int] = None) -> PerformanceMetrics:
        """Start monitoring an operation."""
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            input_size_bytes=input_size,
            memory_start_mb=self._get_memory_usage()
        )
        
        self._active_operations[operation_name] = metrics
        return metrics
    
    def end_operation(self, operation_name: str, success: bool = True, 
                     error_message: Optional[str] = None, 
                     output_size: Optional[int] = None) -> Optional[PerformanceMetrics]:
        """End monitoring an operation and record final metrics."""
        if operation_name not in self._active_operations:
            return None
        
        metrics = self._active_operations[operation_name]
        metrics.end_time = datetime.utcnow()
        metrics.duration_ms = int((metrics.end_time - metrics.start_time).total_seconds() * 1000)
        metrics.memory_end_mb = self._get_memory_usage()
        metrics.output_size_bytes = output_size
        metrics.success = success
        metrics.error_message = error_message
        
        # Calculate memory delta
        if metrics.memory_start_mb and metrics.memory_end_mb:
            metrics.memory_peak_mb = max(metrics.memory_start_mb, metrics.memory_end_mb)
        
        # Store in history
        self.metrics_history.append(metrics)
        
        # Clean up active operations
        del self._active_operations[operation_name]
        
        return metrics
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation type."""
        operation_metrics = [m for m in self.metrics_history if m.operation_name == operation_name]
        
        if not operation_metrics:
            return {"operation": operation_name, "count": 0}
        
        durations = [m.duration_ms for m in operation_metrics if m.duration_ms is not None]
        memory_usage = [m.memory_peak_mb for m in operation_metrics if m.memory_peak_mb is not None]
        success_count = sum(1 for m in operation_metrics if m.success)
        
        stats = {
            "operation": operation_name,
            "count": len(operation_metrics),
            "success_rate": success_count / len(operation_metrics) if operation_metrics else 0,
            "timing": {
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "total_duration_ms": sum(durations) if durations else 0
            }
        }
        
        if memory_usage:
            stats["memory"] = {
                "avg_peak_mb": sum(memory_usage) / len(memory_usage),
                "min_peak_mb": min(memory_usage),
                "max_peak_mb": max(memory_usage)
            }
        
        return stats
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        operation_names = set(m.operation_name for m in self.metrics_history)
        
        stats = {
            "summary": {
                "total_operations": len(self.metrics_history),
                "unique_operation_types": len(operation_names),
                "success_rate": sum(1 for m in self.metrics_history if m.success) / len(self.metrics_history) if self.metrics_history else 0
            },
            "operations": {}
        }
        
        for op_name in operation_names:
            stats["operations"][op_name] = self.get_operation_stats(op_name)
        
        return stats
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent performance metrics."""
        recent = self.metrics_history[-limit:] if len(self.metrics_history) > limit else self.metrics_history
        return [asdict(m) for m in recent]
    
    def clear_history(self):
        """Clear performance metrics history."""
        self.metrics_history.clear()
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # psutil not available
            return None
        except Exception:
            # Any other error
            return None
    
    def log_performance_summary(self, logger_instance, request_id: str):
        """Log a performance summary using the structured logger."""
        if not self.metrics_history:
            return
        
        recent_metrics = self.get_recent_metrics(5)  # Last 5 operations
        all_stats = self.get_all_stats()
        
        performance_data = {
            "recent_operations": recent_metrics,
            "overall_stats": all_stats
        }
        
        logger_instance._log(
            level=logger_instance.LogLevel.INFO,
            message="Performance summary",
            request_id=request_id,
            extra_data=performance_data
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for easy performance monitoring
def monitor_performance(operation_name: str):
    """
    Decorator to automatically monitor function performance.
    
    Usage:
        @monitor_performance("schedule_generation")
        def generate_schedule():
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with performance_monitor.monitor_operation(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator