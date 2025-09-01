"""
Test health endpoints functionality.
"""

import json
import sys
from unittest.mock import Mock

# Add the current directory to Python path for imports
sys.path.insert(0, '.')

from api.healthz import handler as healthz_handler
from api.readyz import handler as readyz_handler
from api.metrics import handler as metrics_handler


def test_healthz_endpoint():
    """Test basic health check endpoint."""
    print("Testing /api/healthz endpoint...")
    
    # Mock request
    request = Mock()
    request.method = "GET"
    
    # Call handler
    status, body, headers = healthz_handler(request)
    
    # Parse response
    response_data = json.loads(body)
    
    # Assertions
    assert status == 200, f"Expected 200, got {status}"
    assert response_data["status"] == "healthy", f"Expected healthy status, got {response_data['status']}"
    assert "timestamp" in response_data, "Missing timestamp"
    assert response_data["service"] == "scheduler-api", "Wrong service name"
    
    print("✓ Health check endpoint working correctly")


def test_readyz_endpoint():
    """Test readiness check endpoint."""
    print("Testing /api/readyz endpoint...")
    
    # Mock request
    request = Mock()
    request.method = "GET"
    
    # Call handler
    status, body, headers = readyz_handler(request)
    
    # Parse response
    response_data = json.loads(body)
    
    # Assertions
    assert status in [200, 503], f"Expected 200 or 503, got {status}"
    assert "status" in response_data, "Missing status"
    assert "checks" in response_data, "Missing checks"
    assert "dependencies" in response_data["checks"], "Missing dependency checks"
    assert "modules" in response_data["checks"], "Missing module checks"
    assert "python" in response_data["checks"], "Missing Python version check"
    
    print(f"✓ Readiness check endpoint working correctly (status: {response_data['status']})")
    
    # Print check details for debugging
    for check_name, check_result in response_data["checks"].items():
        print(f"  {check_name}: {check_result['status']} - {check_result['message']}")


def test_metrics_endpoint():
    """Test metrics endpoint."""
    print("Testing /api/metrics endpoint...")
    
    # Mock request
    request = Mock()
    request.method = "GET"
    
    # Call handler (metrics disabled by default)
    status, body, headers = metrics_handler(request)
    
    # Should return 404 when disabled
    assert status == 404, f"Expected 404 when disabled, got {status}"
    
    print("✓ Metrics endpoint correctly disabled by default")


def test_method_not_allowed():
    """Test that endpoints reject non-GET requests."""
    print("Testing method not allowed responses...")
    
    # Mock POST request
    request = Mock()
    request.method = "POST"
    
    # Test all endpoints
    endpoints = [healthz_handler, readyz_handler, metrics_handler]
    
    for handler in endpoints:
        status, body, headers = handler(request)
        assert status == 405, f"Expected 405 for POST request, got {status}"
    
    print("✓ All endpoints correctly reject non-GET requests")


if __name__ == "__main__":
    print("Running health endpoint tests...\n")
    
    try:
        test_healthz_endpoint()
        test_readyz_endpoint()
        test_metrics_endpoint()
        test_method_not_allowed()
        
        print("\n✅ All health endpoint tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)