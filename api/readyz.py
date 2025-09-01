"""
Readiness check endpoint for monitoring.
Validates dependencies and cold start status.
"""

import json
import sys
import importlib
from datetime import datetime
from typing import Dict, Any, List
from lib.rate_limiter import check_request_limits, add_security_headers, RateLimitExceeded


def handler(request):
    """Readiness check endpoint with dependency validation."""
    
    if request.method != "GET":
        headers = add_security_headers({"Content-Type": "application/json"})
        return (405, json.dumps({"error": "Method not allowed"}), headers)
    
    # Rate limiting for readiness checks
    try:
        rate_limit_headers = check_request_limits(request, max_requests=500, window_seconds=3600)
    except RateLimitExceeded as e:
        headers = add_security_headers({"Content-Type": "application/json", "Retry-After": str(e.retry_after)})
        return (429, json.dumps({"error": "Rate limit exceeded"}), headers)
    except Exception:
        rate_limit_headers = {}  # Continue without rate limiting if check fails
    
    readiness_data = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "scheduler-api",
        "version": "2.0",
        "checks": {}
    }
    
    # Check critical dependencies
    dependency_checks = _check_dependencies()
    readiness_data["checks"]["dependencies"] = dependency_checks
    
    # Check if we can import core modules
    module_checks = _check_core_modules()
    readiness_data["checks"]["modules"] = module_checks
    
    # Check Python version
    python_check = _check_python_version()
    readiness_data["checks"]["python"] = python_check
    
    # Determine overall status
    all_checks_passed = all([
        dependency_checks["status"] == "pass",
        module_checks["status"] == "pass", 
        python_check["status"] == "pass"
    ])
    
    headers = {
        "Content-Type": "application/json",
        **rate_limit_headers
    }
    headers = add_security_headers(headers)
    
    if not all_checks_passed:
        readiness_data["status"] = "not_ready"
        return (503, json.dumps(readiness_data), headers)
    
    return (200, json.dumps(readiness_data), headers)


def _check_dependencies() -> Dict[str, Any]:
    """Check if critical Python dependencies are available."""
    required_packages = [
        "pandas",
        "pydantic", 
        "openpyxl"
    ]
    
    missing_packages = []
    available_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            available_packages.append(package)
        except ImportError:
            missing_packages.append(package)
    
    return {
        "status": "pass" if not missing_packages else "fail",
        "available": available_packages,
        "missing": missing_packages,
        "message": "All dependencies available" if not missing_packages else f"Missing packages: {', '.join(missing_packages)}"
    }


def _check_core_modules() -> Dict[str, Any]:
    """Check if core application modules can be imported."""
    core_modules = [
        "schedule_core",
        "export_manager", 
        "models",
        "lib.logging_utils"
    ]
    
    failed_imports = []
    successful_imports = []
    
    for module in core_modules:
        try:
            importlib.import_module(module)
            successful_imports.append(module)
        except Exception as e:
            failed_imports.append({"module": module, "error": str(e)})
    
    return {
        "status": "pass" if not failed_imports else "fail",
        "successful": successful_imports,
        "failed": failed_imports,
        "message": "All core modules available" if not failed_imports else f"Failed to import {len(failed_imports)} modules"
    }


def _check_python_version() -> Dict[str, Any]:
    """Check Python version compatibility."""
    version_info = sys.version_info
    version_string = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    # Require Python 3.8+
    is_compatible = version_info >= (3, 8)
    
    return {
        "status": "pass" if is_compatible else "fail",
        "version": version_string,
        "required": ">=3.8",
        "message": f"Python {version_string} is compatible" if is_compatible else f"Python {version_string} is below minimum required version 3.8"
    }