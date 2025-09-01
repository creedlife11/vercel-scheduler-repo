# Vercel Python serverless function
import json
import io
import uuid
from datetime import datetime, date
from typing import List, Dict, Any
import pandas as pd
from pydantic import ValidationError
from schedule_core import make_schedule, make_enhanced_schedule, nearest_previous_sunday
from export_manager import ExportManager, generate_filename
from models import ScheduleRequest, APIErrorResponse, ValidationError as CustomValidationError
from lib.logging_utils import logger
from lib.performance_monitor import performance_monitor
from lib.feature_flags import (
    feature_flags,
    is_fairness_reporting_enabled,
    is_decision_logging_enabled,
    is_performance_monitoring_enabled,
    get_max_weeks_allowed
)
from lib.config_manager import get_config
from lib.auth_middleware import (
    require_role, 
    AuthenticationError, 
    AuthorizationError, 
    log_audit_event,
    hash_engineer_names
)
from lib.rate_limiter import (
    check_request_limits,
    validate_request_size,
    validate_input_limits,
    sanitize_input_data,
    add_security_headers,
    RateLimitExceeded
)
from lib.audit_logger import log_schedule_generation_event, log_artifact_access_event
from lib.team_storage import store_team_artifact
from lib.rate_limiter import get_client_ip

def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def handler(request):
    # Generate unique request ID for tracking
    request_id = logger.generate_request_id()
    
    if request.method != "POST":
        error_response = APIErrorResponse(
            error="Method not allowed. Use POST",
            request_id=request_id
        )
        return _resp(405, error_response.dict(), headers={"Allow": "POST"})

    # Security checks: request size validation
    try:
        validate_request_size(request, max_size_mb=2.0)  # 2MB limit
    except ValueError as e:
        error_response = APIErrorResponse(
            error="Request too large",
            details=[CustomValidationError(
                field="request_size",
                message=str(e),
                code="REQUEST_TOO_LARGE"
            )],
            request_id=request_id
        )
        return _resp(413, error_response.dict())

    # Authentication and authorization check (if enabled)
    user = None
    if feature_flags.is_enabled("enableAuthenticationSystem"):
        try:
            user = require_role(request, ["EDITOR", "ADMIN"])
            
            # Log authentication success
            log_audit_event(
                user.id, 
                "SCHEDULE_GENERATION_ATTEMPT", 
                request_id,
                {"role": user.role, "teams": len(user.teams)},
                request
            )
            
        except AuthenticationError as e:
            error_response = APIErrorResponse(
                error="Authentication required",
                details=[CustomValidationError(
                    field="authentication",
                    message=e.message,
                    code=e.code
                )],
                request_id=request_id
            )
            return _resp(401, error_response.dict())
        except AuthorizationError as e:
            error_response = APIErrorResponse(
                error="Insufficient permissions",
                details=[CustomValidationError(
                    field="authorization",
                    message=e.message,
                    code=e.code
                )],
                request_id=request_id
            )
            return _resp(403, error_response.dict())
        except Exception as e:
            logger.log_error(request_id, e, "Authentication check failed")
            error_response = APIErrorResponse(
                error="Authentication check failed",
                request_id=request_id
            )
            return _resp(500, error_response.dict())
    else:
        # Create a default user object when auth is disabled
        from dataclasses import dataclass
        @dataclass
        class DefaultUser:
            id: str = "anonymous"
            role: str = "EDITOR"
            teams: list = None
            
            def __post_init__(self):
                if self.teams is None:
                    self.teams = []
        
        user = DefaultUser()

    # Rate limiting check (if enabled)
    rate_limit_headers = {}
    if feature_flags.is_enabled("enableRateLimiting"):
        try:
            # Different limits based on user role
            if user.role == "ADMIN":
                rate_limit_headers = check_request_limits(request, user.id, max_requests=200, window_seconds=3600)
            else:
                rate_limit_headers = check_request_limits(request, user.id, max_requests=50, window_seconds=3600)
                
        except RateLimitExceeded as e:
        error_response = APIErrorResponse(
            error="Rate limit exceeded",
            details=[CustomValidationError(
                field="rate_limit",
                message=e.message,
                code="RATE_LIMIT_EXCEEDED"
            )],
            request_id=request_id
        )
        headers = {"Retry-After": str(e.retry_after)}
        return _resp(429, error_response.dict(), headers)
    except Exception as e:
        logger.log_error(request_id, e, "Rate limit check failed")
        rate_limit_headers = {}  # Continue without rate limiting if check fails

    try:
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        raw_data = json.loads(body) if body else {}
        
        # Input sanitization
        raw_data = sanitize_input_data(raw_data)
        
        # Input validation for security limits
        validate_input_limits(raw_data)
        
        # Start request tracking with privacy-aware logging
        # Hash engineer names for privacy in logs
        safe_data = raw_data.copy()
        if 'engineers' in safe_data and isinstance(safe_data['engineers'], list):
            safe_data['engineers'] = hash_engineer_names(safe_data['engineers'])
        
        metrics = logger.start_request(request_id, safe_data)
        
    except json.JSONDecodeError as e:
        logger.log_error(request_id, e, "JSON parsing failed")
        error_response = APIErrorResponse(
            error="Invalid JSON in request body",
            details=[CustomValidationError(
                field="body",
                message=f"JSON parsing failed: {str(e)}",
                code="invalid_json"
            )],
            request_id=request_id
        )
        return _resp(400, error_response.dict())
    except ValueError as e:
        # Input validation errors
        logger.log_error(request_id, e, "Input validation failed")
        error_response = APIErrorResponse(
            error="Input validation failed",
            details=[CustomValidationError(
                field="input_validation",
                message=str(e),
                code="INVALID_INPUT"
            )],
            request_id=request_id
        )
        return _resp(400, error_response.dict())
    except Exception as e:
        logger.log_error(request_id, e, "Failed to read request body")
        error_response = APIErrorResponse(
            error="Failed to read request body",
            request_id=request_id
        )
        return _resp(400, error_response.dict())

    # Validate request using Pydantic with detailed error handling
    try:
        # Handle start_sunday defaulting
        if "start_sunday" not in raw_data or not raw_data["start_sunday"]:
            raw_data["start_sunday"] = nearest_previous_sunday(date.today()).isoformat()
        
        # Validate the complete request
        validated_request = ScheduleRequest(**raw_data)
        
        engineers = validated_request.engineers
        start_sunday = validated_request.start_sunday
        weeks = validated_request.weeks
        seeds = validated_request.seeds.dict()
        leave_list = [{"Engineer": entry.engineer, "Date": entry.date, "Reason": entry.reason} 
                     for entry in validated_request.leave]
        
    except ValidationError as e:
        # Log validation errors with structured details
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            logger.log_validation_error(request_id, field_path, error["msg"], error.get("input"))
        
        # Convert Pydantic validation errors to structured format
        validation_errors = []
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            validation_errors.append(CustomValidationError(
                field=field_path,
                message=error["msg"],
                code=error["type"],
                value=error.get("input")
            ))
        
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Request validation failed",
            details=validation_errors,
            request_id=request_id
        )
        return _resp(422, error_response.dict())
    
    except Exception as e:
        logger.log_error(request_id, e, "Unexpected validation error")
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Unexpected validation error",
            details=[CustomValidationError(
                field="unknown",
                message=str(e),
                code="validation_error"
            )],
            request_id=request_id
        )
        return _resp(422, error_response.dict())

    leave_df = pd.DataFrame(leave_list, columns=["Engineer","Date","Reason"]) if leave_list else pd.DataFrame(columns=["Engineer","Date","Reason"])

    # Log schedule generation start with hashed names for privacy
    hashed_engineers = hash_engineer_names(engineers)
    logger.log_schedule_generation(request_id, hashed_engineers, weeks, len(leave_list))
    
    # Determine team ID for storage (use first team if available, otherwise create default)
    team_id = None
    if user.teams and len(user.teams) > 0:
        team_id = user.teams[0].get('id') if isinstance(user.teams[0], dict) else None
    
    if not team_id:
        team_id = f"user_{user.id}"  # Fallback to user-specific team

    try:
        # Use enhanced schedule generation with optional performance monitoring
        if is_performance_monitoring_enabled(user.id):
            with performance_monitor.monitor_operation("schedule_generation", input_size=len(json.dumps(raw_data, default=str))):
                schedule_result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
            
            with performance_monitor.monitor_operation("export_manager_init"):
                export_manager = ExportManager(schedule_result)
        else:
            schedule_result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
            export_manager = ExportManager(schedule_result)
    except AssertionError as e:
        logger.log_error(request_id, e, "Schedule generation constraint violation")
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Schedule generation constraint violation",
            details=[CustomValidationError(
                field="schedule_constraints",
                message=str(e),
                code="constraint_violation"
            )],
            request_id=request_id
        )
        return _resp(400, error_response.dict())
    except ValueError as e:
        logger.log_error(request_id, e, "Invalid schedule parameters")
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Invalid schedule parameters",
            details=[CustomValidationError(
                field="schedule_parameters",
                message=str(e),
                code="invalid_parameters"
            )],
            request_id=request_id
        )
        return _resp(400, error_response.dict())
    except Exception as e:
        logger.log_error(request_id, e, "Schedule generation failed")
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Schedule generation failed",
            details=[CustomValidationError(
                field="schedule_generation",
                message=f"Unexpected error: {str(e)}",
                code="generation_error"
            )],
            request_id=request_id
        )
        return _resp(500, error_response.dict())

    fmt = (raw_data.get("format") or "csv").lower()
    
    # Generate descriptive filename
    config_name = "default"  # Could be enhanced to detect preset names
    filename = generate_filename(fmt, schedule_result.metadata, config_name)
    
    try:
        if fmt == "xlsx":
            if is_performance_monitoring_enabled(user.id):
                with performance_monitor.monitor_operation("xlsx_export"):
                    xlsx_bytes = export_manager.to_xlsx()
            else:
                xlsx_bytes = export_manager.to_xlsx()
            logger.log_export_generation(request_id, "xlsx", len(xlsx_bytes))
            
            # Store artifact for team access
            try:
                artifact_metadata = {
                    "engineer_count": len(engineers),
                    "weeks": weeks,
                    "leave_entries": len(leave_list),
                    "request_id": request_id
                }
                artifact_id = store_team_artifact(
                    team_id, filename, "XLSX", xlsx_bytes, user.id, artifact_metadata
                )
                
                # Log artifact creation
                log_artifact_access_event(
                    user.id, team_id, artifact_id, "CREATED", 
                    ip_address=get_client_ip(request)
                )
            except Exception as e:
                logger.log_error(request_id, e, "Failed to store team artifact")
            
            # Log schedule generation success
            log_schedule_generation_event(
                user.id, team_id, len(engineers), weeks, "xlsx", 
                success=True, ip_address=get_client_ip(request)
            )
            
            logger.end_request(request_id, success=True, output_size=len(xlsx_bytes))
            
            # Log performance summary
            performance_monitor.log_performance_summary(logger, request_id)
            
            headers = {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-ID": request_id,
                **rate_limit_headers
            }
            headers = add_security_headers(headers)
            return (200, xlsx_bytes, headers)
        elif fmt == "json":
            if is_performance_monitoring_enabled(user.id):
                with performance_monitor.monitor_operation("json_export"):
                    json_str = export_manager.to_json_string()
                    json_bytes = json_str.encode("utf-8")
            else:
                json_str = export_manager.to_json_string()
                json_bytes = json_str.encode("utf-8")
            logger.log_export_generation(request_id, "json", len(json_bytes))
            
            # Store artifact for team access
            try:
                artifact_metadata = {
                    "engineer_count": len(engineers),
                    "weeks": weeks,
                    "leave_entries": len(leave_list),
                    "request_id": request_id
                }
                artifact_id = store_team_artifact(
                    team_id, filename, "JSON", json_bytes, user.id, artifact_metadata
                )
                
                # Log artifact creation
                log_artifact_access_event(
                    user.id, team_id, artifact_id, "CREATED", 
                    ip_address=get_client_ip(request)
                )
            except Exception as e:
                logger.log_error(request_id, e, "Failed to store team artifact")
            
            # Log schedule generation success
            log_schedule_generation_event(
                user.id, team_id, len(engineers), weeks, "json", 
                success=True, ip_address=get_client_ip(request)
            )
            
            logger.end_request(request_id, success=True, output_size=len(json_bytes))
            
            # Log performance summary
            performance_monitor.log_performance_summary(logger, request_id)
            
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-ID": request_id,
                **rate_limit_headers
            }
            headers = add_security_headers(headers)
            return (200, json_bytes, headers)
        else:  # csv (default)
            if is_performance_monitoring_enabled(user.id):
                with performance_monitor.monitor_operation("csv_export"):
                    csv_bytes = export_manager.to_csv_bytes()
            else:
                csv_bytes = export_manager.to_csv_bytes()
            logger.log_export_generation(request_id, "csv", len(csv_bytes))
            
            # Store artifact for team access
            try:
                artifact_metadata = {
                    "engineer_count": len(engineers),
                    "weeks": weeks,
                    "leave_entries": len(leave_list),
                    "request_id": request_id
                }
                artifact_id = store_team_artifact(
                    team_id, filename, "CSV", csv_bytes, user.id, artifact_metadata
                )
                
                # Log artifact creation
                log_artifact_access_event(
                    user.id, team_id, artifact_id, "CREATED", 
                    ip_address=get_client_ip(request)
                )
            except Exception as e:
                logger.log_error(request_id, e, "Failed to store team artifact")
            
            # Log schedule generation success
            log_schedule_generation_event(
                user.id, team_id, len(engineers), weeks, "csv", 
                success=True, ip_address=get_client_ip(request)
            )
            
            logger.end_request(request_id, success=True, output_size=len(csv_bytes))
            
            # Log performance summary
            performance_monitor.log_performance_summary(logger, request_id)
            
            headers = {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-ID": request_id,
                **rate_limit_headers
            }
            headers = add_security_headers(headers)
            return (200, csv_bytes, headers)
    except Exception as e:
        logger.log_error(request_id, e, f"Export generation failed for format {fmt}")
        logger.end_request(request_id, success=False)
        error_response = APIErrorResponse(
            error="Export generation failed",
            details=[CustomValidationError(
                field="export_generation",
                message=f"Failed to generate {fmt.upper()} export: {str(e)}",
                code="export_error"
            )],
            request_id=request_id
        )
        return _resp(500, error_response.dict())

def _resp(status: int, body: Any, headers: Dict[str, str] = None) -> tuple:
    """Create a standardized HTTP response."""
    if isinstance(body, (dict, list)):
        payload = json.dumps(body, default=str).encode("utf-8")
        base_headers = {"Content-Type": "application/json; charset=utf-8"}
        if headers: 
            base_headers.update(headers)
        base_headers = add_security_headers(base_headers)
        return (status, payload, base_headers)
    else:
        final_headers = add_security_headers(headers or {})
        return (status, body, final_headers)
