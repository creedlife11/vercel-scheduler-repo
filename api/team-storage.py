"""
Team-scoped artifact storage API endpoint.
Handles team artifact management with access control.
"""

import json
from typing import Dict, Any
from lib.team_storage import team_storage, verify_team_access
from lib.audit_logger import log_artifact_access_event
from lib.auth_middleware import require_authentication, AuthenticationError, get_client_ip
from lib.rate_limiter import check_request_limits, add_security_headers, RateLimitExceeded


def handler(request):
    """Team storage API handler."""
    
    if request.method != "POST":
        headers = add_security_headers({"Content-Type": "application/json"})
        return (405, json.dumps({"error": "Method not allowed"}), headers)
    
    # Authentication required
    try:
        user = require_authentication(request)
    except AuthenticationError as e:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (401, json.dumps({"error": e.message}), headers)
    except Exception as e:
        headers = add_security_headers({"Content-Type": "application/json"})
        return (500, json.dumps({"error": "Authentication check failed"}), headers)
    
    # Rate limiting
    try:
        rate_limit_headers = check_request_limits(request, user.id, max_requests=200, window_seconds=3600)
    except RateLimitExceeded as e:
        headers = add_security_headers({
            "Content-Type": "application/json", 
            "Retry-After": str(e.retry_after)
        })
        return (429, json.dumps({"error": e.message}), headers)
    except Exception:
        rate_limit_headers = {}
    
    # Parse request body
    try:
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (400, json.dumps({"error": "Invalid JSON"}), headers)
    
    action = data.get('action')
    team_id = data.get('team_id')
    
    if not team_id:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (400, json.dumps({"error": "team_id required"}), headers)
    
    # Verify team access
    if user.role != "ADMIN" and not verify_team_access(user.teams, team_id):
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (403, json.dumps({"error": "Team access denied"}), headers)
    
    try:
        if action == "list" or not action:
            return handle_list_artifacts(data, user, rate_limit_headers)
        elif action == "get":
            return handle_get_artifact(data, user, request, rate_limit_headers)
        elif action == "delete":
            return handle_delete_artifact(data, user, request, rate_limit_headers)
        else:
            headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
            return (400, json.dumps({"error": f"Unknown action: {action}"}), headers)
            
    except Exception as e:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (500, json.dumps({"error": f"Operation failed: {str(e)}"}), headers)


def handle_list_artifacts(data: Dict[str, Any], user, rate_limit_headers: Dict[str, str]):
    """List artifacts for a team."""
    team_id = data['team_id']
    limit = min(data.get('limit', 50), 100)  # Cap at 100
    
    try:
        artifacts = team_storage.list_team_artifacts(team_id, limit)
        
        # Convert to serializable format
        artifact_list = []
        for artifact in artifacts:
            artifact_dict = {
                'id': artifact.id,
                'name': artifact.name,
                'type': artifact.artifact_type,
                'created_at': artifact.created_at.isoformat(),
                'created_by': artifact.created_by,
                'size_bytes': artifact.size_bytes,
                'engineer_count': artifact.engineer_count,
                'weeks': artifact.weeks
            }
            artifact_list.append(artifact_dict)
        
        # Log access
        log_artifact_access_event(
            user.id, team_id, f"list_{len(artifact_list)}", "LISTED",
            success=True
        )
        
        headers = add_security_headers({
            "Content-Type": "application/json",
            **rate_limit_headers
        })
        
        return (200, json.dumps({
            "artifacts": artifact_list,
            "count": len(artifact_list)
        }), headers)
        
    except Exception as e:
        log_artifact_access_event(
            user.id, team_id, "list", "LIST_FAILED",
            success=False, error_message=str(e)
        )
        raise


def handle_get_artifact(data: Dict[str, Any], user, request, rate_limit_headers: Dict[str, str]):
    """Get a specific artifact."""
    team_id = data['team_id']
    artifact_id = data.get('artifact_id')
    
    if not artifact_id:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (400, json.dumps({"error": "artifact_id required"}), headers)
    
    try:
        # Get artifact metadata
        metadata = team_storage.get_artifact_metadata(team_id, artifact_id)
        if not metadata:
            log_artifact_access_event(
                user.id, team_id, artifact_id, "GET_FAILED",
                success=False, error_message="Artifact not found",
                ip_address=get_client_ip(request)
            )
            headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
            return (404, json.dumps({"error": "Artifact not found"}), headers)
        
        # Get artifact data
        artifact_data = team_storage.get_artifact(team_id, artifact_id)
        if not artifact_data:
            log_artifact_access_event(
                user.id, team_id, artifact_id, "GET_FAILED",
                success=False, error_message="Artifact data not found",
                ip_address=get_client_ip(request)
            )
            headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
            return (404, json.dumps({"error": "Artifact data not found"}), headers)
        
        # Log successful access
        log_artifact_access_event(
            user.id, team_id, artifact_id, "DOWNLOADED",
            success=True, ip_address=get_client_ip(request)
        )
        
        # Determine content type
        content_type_map = {
            "CSV": "text/csv; charset=utf-8",
            "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "JSON": "application/json; charset=utf-8"
        }
        content_type = content_type_map.get(metadata.artifact_type, "application/octet-stream")
        
        headers = add_security_headers({
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{metadata.name}"',
            **rate_limit_headers
        })
        
        return (200, artifact_data, headers)
        
    except Exception as e:
        log_artifact_access_event(
            user.id, team_id, artifact_id, "GET_FAILED",
            success=False, error_message=str(e),
            ip_address=get_client_ip(request)
        )
        raise


def handle_delete_artifact(data: Dict[str, Any], user, request, rate_limit_headers: Dict[str, str]):
    """Delete a specific artifact."""
    team_id = data['team_id']
    artifact_id = data.get('artifact_id')
    
    if not artifact_id:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (400, json.dumps({"error": "artifact_id required"}), headers)
    
    # Only editors and admins can delete
    if user.role not in ["EDITOR", "ADMIN"]:
        headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
        return (403, json.dumps({"error": "Insufficient permissions"}), headers)
    
    try:
        # Check if artifact exists
        metadata = team_storage.get_artifact_metadata(team_id, artifact_id)
        if not metadata:
            log_artifact_access_event(
                user.id, team_id, artifact_id, "DELETE_FAILED",
                success=False, error_message="Artifact not found",
                ip_address=get_client_ip(request)
            )
            headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
            return (404, json.dumps({"error": "Artifact not found"}), headers)
        
        # Delete the artifact
        deleted = team_storage.delete_artifact(team_id, artifact_id)
        
        if deleted:
            log_artifact_access_event(
                user.id, team_id, artifact_id, "DELETED",
                success=True, ip_address=get_client_ip(request)
            )
            
            headers = add_security_headers({
                "Content-Type": "application/json",
                **rate_limit_headers
            })
            return (200, json.dumps({"success": True}), headers)
        else:
            log_artifact_access_event(
                user.id, team_id, artifact_id, "DELETE_FAILED",
                success=False, error_message="Delete operation failed",
                ip_address=get_client_ip(request)
            )
            headers = add_security_headers({"Content-Type": "application/json", **rate_limit_headers})
            return (500, json.dumps({"error": "Delete operation failed"}), headers)
        
    except Exception as e:
        log_artifact_access_event(
            user.id, team_id, artifact_id, "DELETE_FAILED",
            success=False, error_message=str(e),
            ip_address=get_client_ip(request)
        )
        raise