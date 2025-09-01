"""
Test monitoring and reliability infrastructure.
Tests structured logging, performance monitoring, and invariant checking.
"""

import sys
import json
import pandas as pd
from datetime import date, datetime
from unittest.mock import Mock, patch

# Add the current directory to Python path for imports
sys.path.insert(0, '.')

from lib.logging_utils import StructuredLogger, LogLevel, RequestMetrics
from lib.performance_monitor import PerformanceMonitor, PerformanceMetrics
from lib.invariant_checker import ScheduleInvariantChecker, InvariantType


def test_structured_logging():
    """Test structured logging functionality."""
    print("Testing structured logging...")
    
    logger = StructuredLogger("test-component")
    
    # Test request ID generation
    request_id = logger.generate_request_id()
    assert len(request_id) == 8, f"Request ID should be 8 characters, got {len(request_id)}"
    
    # Test request tracking
    input_data = {"engineers": ["Alice", "Bob"], "weeks": 4}
    metrics = logger.start_request(request_id, input_data)
    
    assert metrics.request_id == request_id
    assert metrics.engineer_count == 2
    assert metrics.weeks == 4
    
    # Test ending request
    final_metrics = logger.end_request(request_id, success=True, output_size=1024)
    assert final_metrics is not None
    assert final_metrics.processing_time_ms is not None
    assert final_metrics.output_size == 1024
    
    print("✓ Structured logging working correctly")


def test_performance_monitoring():
    """Test performance monitoring functionality."""
    print("Testing performance monitoring...")
    
    monitor = PerformanceMonitor()
    
    # Test operation monitoring
    with monitor.monitor_operation("test_operation", input_size=512) as metrics:
        # Simulate some work
        import time
        time.sleep(0.01)  # 10ms
    
    # Check metrics were recorded
    stats = monitor.get_operation_stats("test_operation")
    assert stats["count"] == 1
    assert stats["success_rate"] == 1.0
    assert stats["timing"]["avg_duration_ms"] >= 10  # Should be at least 10ms
    
    # Test multiple operations
    for i in range(3):
        with monitor.monitor_operation("batch_test"):
            pass
    
    batch_stats = monitor.get_operation_stats("batch_test")
    assert batch_stats["count"] == 3
    
    # Test all stats
    all_stats = monitor.get_all_stats()
    assert all_stats["summary"]["total_operations"] == 4  # 1 + 3
    assert "test_operation" in all_stats["operations"]
    assert "batch_test" in all_stats["operations"]
    
    print("✓ Performance monitoring working correctly")


def test_invariant_checking():
    """Test scheduling invariant checking."""
    print("Testing invariant checking...")
    
    engineers = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank"]
    checker = ScheduleInvariantChecker(engineers)
    
    # Create test schedule data with violations
    test_data = {
        'Date': ['2025-01-05', '2025-01-06'],  # Sunday, Monday
        'Day': ['Sunday', 'Monday'],
        'OnCall': ['Alice', ''],  # Violation: oncall on Sunday
        'Status 1': ['WORK', 'Alice'],  # Violation: engineer name in status
        '1) Alice': ['Alice', '9:00'],  # Violation: time string in engineer field
        'WeekIndex': [0, 0]
    }
    
    df = pd.DataFrame(test_data)
    violations = checker.check_all_invariants(df)
    
    # Should find violations
    assert len(violations) > 0, "Should have found invariant violations"
    
    # Check specific violation types
    violation_types = [v.violation_type for v in violations]
    assert InvariantType.NO_ONCALL_WEEKENDS in violation_types, "Should detect weekend oncall violation"
    assert InvariantType.STATUS_FIELD_INTEGRITY in violation_types, "Should detect status field violation"
    assert InvariantType.ENGINEER_FIELD_INTEGRITY in violation_types, "Should detect engineer field violation"
    
    # Test CSV column count checking
    csv_content = "Date,Day,OnCall\n2025-01-05,Sunday,Alice\n2025-01-06,Monday"  # Missing column
    csv_violations = checker.check_all_invariants(pd.DataFrame(), csv_content)
    
    csv_violation_types = [v.violation_type for v in csv_violations]
    assert InvariantType.CSV_COLUMN_COUNT in csv_violation_types, "Should detect CSV column count violation"
    
    # Test violation summary
    summary = checker.get_violation_summary()
    assert summary["total_violations"] > 0
    assert "error" in summary["by_severity"]
    
    print("✓ Invariant checking working correctly")


def test_fairness_distribution_checking():
    """Test fairness distribution invariant checking."""
    print("Testing fairness distribution checking...")
    
    engineers = ["Alice", "Bob", "Charlie"]
    checker = ScheduleInvariantChecker(engineers)
    
    # Create unfair distribution
    fairness_report = {
        "engineer_stats": {
            "Alice": {"oncall": 5, "weekend": 3},
            "Bob": {"oncall": 1, "weekend": 0},  # Very unfair
            "Charlie": {"oncall": 2, "weekend": 1}
        }
    }
    
    violations = checker.check_fairness_distribution(fairness_report)
    
    # Should detect unfairness
    assert len(violations) > 0, "Should detect fairness violations"
    
    fairness_violation = violations[0]
    assert fairness_violation.violation_type == InvariantType.FAIRNESS_DISTRIBUTION
    assert fairness_violation.severity == "warning"
    
    print("✓ Fairness distribution checking working correctly")


def test_integration_with_mocked_api():
    """Test integration of monitoring components with mocked API calls."""
    print("Testing integration with mocked API...")
    
    # Mock the API request structure
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.body = json.dumps({
        "engineers": ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank"],
        "weeks": 2,
        "seeds": {"weekend": 0, "oncall": 0, "early": 0, "chat": 0},
        "format": "csv"
    })
    
    # Test that we can create a logger and start tracking
    logger = StructuredLogger("api-test")
    request_id = logger.generate_request_id()
    
    raw_data = json.loads(mock_request.body)
    metrics = logger.start_request(request_id, raw_data)
    
    assert metrics.engineer_count == 6
    assert metrics.weeks == 2
    
    # Test performance monitoring
    monitor = PerformanceMonitor()
    
    with monitor.monitor_operation("mock_schedule_generation"):
        # Simulate schedule generation
        pass
    
    with monitor.monitor_operation("mock_export"):
        # Simulate export
        pass
    
    # Verify operations were tracked
    gen_stats = monitor.get_operation_stats("mock_schedule_generation")
    export_stats = monitor.get_operation_stats("mock_export")
    
    assert gen_stats["count"] == 1
    assert export_stats["count"] == 1
    
    # End request tracking
    final_metrics = logger.end_request(request_id, success=True, output_size=2048)
    assert final_metrics.output_size == 2048
    
    print("✓ Integration testing working correctly")


if __name__ == "__main__":
    print("Running monitoring and reliability tests...\n")
    
    try:
        test_structured_logging()
        test_performance_monitoring()
        test_invariant_checking()
        test_fairness_distribution_checking()
        test_integration_with_mocked_api()
        
        print("\n✅ All monitoring and reliability tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)