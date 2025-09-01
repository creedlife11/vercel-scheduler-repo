import json
import jwt
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

@dataclass
class AuthenticatedUser:
    id: str
    email: str
    name: Optional[str]
    role: str
    teams: list

class AuthenticationError(Exception):
    def __init__(self, message: str, code: str = "UNAUTHORIZED"):
        self.message = message
        self.code = code
        super().__init__(message)

class AuthorizationError(Exception):
    def __init__(self, message: str, code: str = "FORBIDDEN"):
        self.message = message
        self.code = code
        super().__init__(message)

def extract_session_from_request(request) -> Optional[Dict[str, Any]]:
    """Extract NextAuth session from request cookies."""
    try:
        # Get session token from cookies
        cookies = {}
        if hasattr(request, 'headers') and 'cookie' in request.headers:
            cookie_header = request.headers['cookie']
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    cookies[key] = value
        
        # Look for NextAuth session token
        session_token = None
        for key, value in cookies.items():
            if 'next-auth.session-token' in key or 'session-token' in key:
                session_token = value
                break
        
        if not session_token:
            return None
        
        # For demo purposes, we'll decode a simple JWT
        # In production, you'd verify against your session store
        try:
            # This is a simplified approach - in production you'd verify the JWT properly
            secret = os.getenv('NEXTAUTH_SECRET', 'your-secret-key')
            payload = jwt.decode(session_token, secret, algorithms=['HS256'], options={"verify_signature": False})
            return payload
        except jwt.InvalidTokenError:
            return None
            
    except Exception:
        return None

def get_authenticated_user(request) -> Optional[AuthenticatedUser]:
    """Get authenticated user from request."""
    session = extract_session_from_request(request)
    
    if not session:
        return None
    
    return AuthenticatedUser(
        id=session.get('sub', ''),
        email=session.get('email', ''),
        name=session.get('name'),
        role=session.get('role', 'VIEWER'),
        teams=session.get('teams', [])
    )

def require_authentication(request) -> AuthenticatedUser:
    """Require authentication and return user or raise exception."""
    user = get_authenticated_user(request)
    
    if not user:
        raise AuthenticationError("Authentication required")
    
    return user

def require_role(request, required_roles: list) -> AuthenticatedUser:
    """Require specific role and return user or raise exception."""
    user = require_authentication(request)
    
    if user.role not in required_roles:
        raise AuthorizationError(
            f"Insufficient permissions. Required: {required_roles}, Current: {user.role}",
            "INSUFFICIENT_PERMISSIONS"
        )
    
    return user

def require_team_access(request, team_id: Optional[str] = None) -> AuthenticatedUser:
    """Require team access and return user or raise exception."""
    user = require_authentication(request)
    
    # Admin users have access to all teams
    if user.role == "ADMIN":
        return user
    
    # If no specific team required, just check authentication
    if not team_id:
        return user
    
    # Check if user has access to the specific team
    user_team_ids = [team.get('id') for team in user.teams if isinstance(team, dict)]
    
    if team_id not in user_team_ids:
        raise AuthorizationError(
            f"Team access denied for team {team_id}",
            "TEAM_ACCESS_DENIED"
        )
    
    return user

def log_audit_event(user_id: str, action: str, resource: Optional[str] = None, 
                   metadata: Optional[Dict[str, Any]] = None, request=None):
    """Log audit event (simplified version - in production would write to database)."""
    try:
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "metadata": metadata,
            "ip_address": get_client_ip(request) if request else None,
            "user_agent": getattr(request, 'headers', {}).get('user-agent') if request else None
        }
        
        # In production, this would write to your audit log database
        print(f"AUDIT: {json.dumps(audit_entry)}")
        
    except Exception as e:
        print(f"Failed to log audit event: {e}")

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

def hash_engineer_names(names: list) -> list:
    """Hash engineer names for privacy in logs."""
    import hashlib
    
    hashed_names = []
    for name in names:
        if isinstance(name, str):
            # Create a consistent hash of the name
            hash_obj = hashlib.sha256(name.encode('utf-8'))
            hashed = f"eng_{hash_obj.hexdigest()[:8]}"
            hashed_names.append(hashed)
        else:
            hashed_names.append(str(name))
    
    return hashed_names