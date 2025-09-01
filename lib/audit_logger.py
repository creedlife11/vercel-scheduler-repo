import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class AuditEvent:
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource: Optional[str]
    team_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None

class AuditLogger:
    """Enhanced audit logging with privacy controls."""
    
    def __init__(self, log_file: str = "./audit.log"):
        self.log_file = log_file
        self.privacy_enabled = os.environ.get("ENABLE_PRIVACY_HASHING", "true").lower() == "true"
    
    def log_event(self, user_id: str, action: str, success: bool = True,
                  resource: Optional[str] = None, team_id: Optional[str] = None,
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None):
        """Log an audit event with privacy controls."""
        
        # Generate unique event ID
        event_id = self._generate_event_id()
        
        # Apply privacy controls to metadata
        safe_metadata = self._apply_privacy_controls(metadata) if metadata else None
        
        # Hash sensitive information if privacy is enabled
        safe_user_id = self._hash_if_enabled(user_id, "user")
        safe_ip = self._hash_if_enabled(ip_address, "ip") if ip_address else None
        
        event = AuditEvent(
            id=event_id,
            timestamp=datetime.utcnow(),
            user_id=safe_user_id,
            action=action,
            resource=resource,
            team_id=team_id,
            ip_address=safe_ip,
            user_agent=user_agent,
            metadata=safe_metadata,
            success=success,
            error_message=error_message
        )
        
        self._write_event(event)
    
    def log_authentication(self, user_id: str, success: bool, ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None, error_message: Optional[str] = None):
        """Log authentication events."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.log_event(
            user_id=user_id,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message
        )
    
    def log_schedule_generation(self, user_id: str, team_id: Optional[str], 
                               engineer_count: int, weeks: int, format_type: str,
                               success: bool = True, error_message: Optional[str] = None,
                               ip_address: Optional[str] = None):
        """Log schedule generation events."""
        metadata = {
            "engineer_count": engineer_count,
            "weeks": weeks,
            "format": format_type
        }
        
        action = "SCHEDULE_GENERATED" if success else "SCHEDULE_GENERATION_FAILED"
        self.log_event(
            user_id=user_id,
            action=action,
            success=success,
            team_id=team_id,
            metadata=metadata,
            error_message=error_message,
            ip_address=ip_address
        )
    
    def log_artifact_access(self, user_id: str, team_id: str, artifact_id: str,
                           action: str, success: bool = True, 
                           error_message: Optional[str] = None,
                           ip_address: Optional[str] = None):
        """Log artifact access events."""
        self.log_event(
            user_id=user_id,
            action=f"ARTIFACT_{action.upper()}",
            success=success,
            resource=artifact_id,
            team_id=team_id,
            error_message=error_message,
            ip_address=ip_address
        )
    
    def log_admin_action(self, user_id: str, action: str, target_resource: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None, success: bool = True,
                        error_message: Optional[str] = None, ip_address: Optional[str] = None):
        """Log administrative actions."""
        self.log_event(
            user_id=user_id,
            action=f"ADMIN_{action.upper()}",
            success=success,
            resource=target_resource,
            metadata=metadata,
            error_message=error_message,
            ip_address=ip_address
        )
    
    def get_audit_trail(self, user_id: Optional[str] = None, team_id: Optional[str] = None,
                       action_filter: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail with filtering (for admin use)."""
        events = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        
                        # Apply filters
                        if user_id and event_data.get('user_id') != user_id:
                            continue
                        if team_id and event_data.get('team_id') != team_id:
                            continue
                        if action_filter and action_filter not in event_data.get('action', ''):
                            continue
                        
                        events.append(event_data)
                        
                        if len(events) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except FileNotFoundError:
            pass
        
        # Return most recent events first
        return list(reversed(events))
    
    def _write_event(self, event: AuditEvent):
        """Write event to audit log file."""
        try:
            with open(self.log_file, 'a') as f:
                event_json = json.dumps(asdict(event), default=str)
                f.write(event_json + '\n')
        except Exception as e:
            # Fallback to console logging if file write fails
            print(f"AUDIT_LOG_ERROR: Failed to write audit event: {e}")
            print(f"AUDIT_EVENT: {json.dumps(asdict(event), default=str)}")
    
    def _apply_privacy_controls(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Apply privacy controls to metadata."""
        if not self.privacy_enabled:
            return metadata
        
        safe_metadata = {}
        
        for key, value in metadata.items():
            if key in ['engineers', 'engineer_names', 'names']:
                # Hash engineer names for privacy
                if isinstance(value, list):
                    safe_metadata[key] = [self._hash_if_enabled(name, "engineer") for name in value]
                else:
                    safe_metadata[key] = self._hash_if_enabled(str(value), "engineer")
            elif key in ['email', 'emails']:
                # Hash email addresses
                if isinstance(value, list):
                    safe_metadata[key] = [self._hash_if_enabled(email, "email") for email in value]
                else:
                    safe_metadata[key] = self._hash_if_enabled(str(value), "email")
            else:
                # Keep other metadata as-is
                safe_metadata[key] = value
        
        return safe_metadata
    
    def _hash_if_enabled(self, value: str, prefix: str = "") -> str:
        """Hash a value if privacy is enabled."""
        if not self.privacy_enabled or not value:
            return value
        
        # Create a consistent hash
        hash_obj = hashlib.sha256(value.encode('utf-8'))
        hashed = hash_obj.hexdigest()[:12]
        
        return f"{prefix}_{hashed}" if prefix else hashed
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        timestamp = datetime.utcnow().isoformat()
        hash_obj = hashlib.sha256(timestamp.encode('utf-8'))
        return hash_obj.hexdigest()[:16]

# Global audit logger instance
audit_logger = AuditLogger()

def log_audit_event(user_id: str, action: str, success: bool = True, **kwargs):
    """Convenience function for logging audit events."""
    audit_logger.log_event(user_id, action, success, **kwargs)

def log_authentication_event(user_id: str, success: bool, **kwargs):
    """Convenience function for logging authentication events."""
    audit_logger.log_authentication(user_id, success, **kwargs)

def log_schedule_generation_event(user_id: str, team_id: Optional[str], **kwargs):
    """Convenience function for logging schedule generation events."""
    audit_logger.log_schedule_generation(user_id, team_id, **kwargs)

def log_artifact_access_event(user_id: str, team_id: str, artifact_id: str, action: str, **kwargs):
    """Convenience function for logging artifact access events."""
    audit_logger.log_artifact_access(user_id, team_id, artifact_id, action, **kwargs)

def get_user_audit_trail(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get audit trail for a specific user."""
    return audit_logger.get_audit_trail(user_id=user_id, limit=limit)

def get_team_audit_trail(team_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get audit trail for a specific team."""
    return audit_logger.get_audit_trail(team_id=team_id, limit=limit)