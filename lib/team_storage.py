import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class ArtifactMetadata:
    id: str
    team_id: str
    name: str
    artifact_type: str  # CSV, XLSX, JSON
    created_at: datetime
    created_by: str
    size_bytes: int
    config_hash: str
    engineer_count: int
    weeks: int

class TeamStorageManager:
    """Manages team-scoped artifact storage and access control."""
    
    def __init__(self, base_path: str = "./team_artifacts"):
        self.base_path = base_path
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Ensure base storage directory exists."""
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_team_directory(self, team_id: str) -> str:
        """Get team-specific storage directory."""
        team_dir = os.path.join(self.base_path, self._sanitize_team_id(team_id))
        os.makedirs(team_dir, exist_ok=True)
        return team_dir
    
    def _sanitize_team_id(self, team_id: str) -> str:
        """Sanitize team ID for safe filesystem usage."""
        # Remove any potentially dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        sanitized = ''.join(c for c in team_id if c in safe_chars)
        return sanitized[:50]  # Limit length
    
    def store_artifact(self, team_id: str, artifact_name: str, artifact_type: str,
                      data: bytes, created_by: str, metadata: Dict[str, Any]) -> str:
        """Store an artifact for a specific team."""
        team_dir = self._get_team_directory(team_id)
        
        # Generate unique artifact ID
        artifact_id = self._generate_artifact_id(team_id, artifact_name, artifact_type)
        
        # Create artifact metadata
        artifact_metadata = ArtifactMetadata(
            id=artifact_id,
            team_id=team_id,
            name=artifact_name,
            artifact_type=artifact_type,
            created_at=datetime.utcnow(),
            created_by=created_by,
            size_bytes=len(data),
            config_hash=self._hash_config(metadata),
            engineer_count=metadata.get('engineer_count', 0),
            weeks=metadata.get('weeks', 0)
        )
        
        # Store the artifact data
        artifact_file = os.path.join(team_dir, f"{artifact_id}.{artifact_type.lower()}")
        with open(artifact_file, 'wb') as f:
            f.write(data)
        
        # Store the metadata
        metadata_file = os.path.join(team_dir, f"{artifact_id}.meta.json")
        with open(metadata_file, 'w') as f:
            json.dump(asdict(artifact_metadata), f, default=str, indent=2)
        
        return artifact_id
    
    def get_artifact(self, team_id: str, artifact_id: str) -> Optional[bytes]:
        """Retrieve an artifact for a specific team."""
        team_dir = self._get_team_directory(team_id)
        
        # Find the artifact file (try different extensions)
        for ext in ['csv', 'xlsx', 'json']:
            artifact_file = os.path.join(team_dir, f"{artifact_id}.{ext}")
            if os.path.exists(artifact_file):
                with open(artifact_file, 'rb') as f:
                    return f.read()
        
        return None
    
    def get_artifact_metadata(self, team_id: str, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Get metadata for a specific artifact."""
        team_dir = self._get_team_directory(team_id)
        metadata_file = os.path.join(team_dir, f"{artifact_id}.meta.json")
        
        if not os.path.exists(metadata_file):
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                # Convert string back to datetime
                data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                return ArtifactMetadata(**data)
        except Exception:
            return None
    
    def list_team_artifacts(self, team_id: str, limit: int = 100) -> List[ArtifactMetadata]:
        """List all artifacts for a team."""
        team_dir = self._get_team_directory(team_id)
        
        artifacts = []
        
        # Find all metadata files
        for filename in os.listdir(team_dir):
            if filename.endswith('.meta.json'):
                artifact_id = filename.replace('.meta.json', '')
                metadata = self.get_artifact_metadata(team_id, artifact_id)
                if metadata:
                    artifacts.append(metadata)
        
        # Sort by creation date (newest first) and limit
        artifacts.sort(key=lambda x: x.created_at, reverse=True)
        return artifacts[:limit]
    
    def delete_artifact(self, team_id: str, artifact_id: str) -> bool:
        """Delete an artifact and its metadata."""
        team_dir = self._get_team_directory(team_id)
        
        deleted = False
        
        # Delete artifact files (try different extensions)
        for ext in ['csv', 'xlsx', 'json']:
            artifact_file = os.path.join(team_dir, f"{artifact_id}.{ext}")
            if os.path.exists(artifact_file):
                os.remove(artifact_file)
                deleted = True
        
        # Delete metadata file
        metadata_file = os.path.join(team_dir, f"{artifact_id}.meta.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
            deleted = True
        
        return deleted
    
    def cleanup_old_artifacts(self, team_id: str, days_old: int = 30) -> int:
        """Clean up artifacts older than specified days."""
        team_dir = self._get_team_directory(team_id)
        cutoff_date = datetime.utcnow().timestamp() - (days_old * 24 * 3600)
        
        deleted_count = 0
        
        for filename in os.listdir(team_dir):
            if filename.endswith('.meta.json'):
                artifact_id = filename.replace('.meta.json', '')
                metadata = self.get_artifact_metadata(team_id, artifact_id)
                
                if metadata and metadata.created_at.timestamp() < cutoff_date:
                    if self.delete_artifact(team_id, artifact_id):
                        deleted_count += 1
        
        return deleted_count
    
    def _generate_artifact_id(self, team_id: str, name: str, artifact_type: str) -> str:
        """Generate a unique artifact ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{team_id}:{name}:{artifact_type}:{timestamp}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    def _hash_config(self, config: Dict[str, Any]) -> str:
        """Create a hash of the configuration for deduplication."""
        # Create a stable string representation of the config
        config_str = json.dumps(config, sort_keys=True, default=str)
        hash_obj = hashlib.sha256(config_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]

# Global storage manager instance
team_storage = TeamStorageManager()

def store_team_artifact(team_id: str, artifact_name: str, artifact_type: str,
                       data: bytes, created_by: str, metadata: Dict[str, Any]) -> str:
    """Store an artifact for a team."""
    return team_storage.store_artifact(team_id, artifact_name, artifact_type, data, created_by, metadata)

def get_team_artifact(team_id: str, artifact_id: str) -> Optional[bytes]:
    """Get an artifact for a team."""
    return team_storage.get_artifact(team_id, artifact_id)

def list_team_artifacts(team_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """List artifacts for a team."""
    artifacts = team_storage.list_team_artifacts(team_id, limit)
    return [asdict(artifact) for artifact in artifacts]

def verify_team_access(user_teams: List[Dict[str, Any]], team_id: str) -> bool:
    """Verify user has access to a specific team."""
    if not user_teams:
        return False
    
    user_team_ids = [team.get('id') for team in user_teams if isinstance(team, dict)]
    return team_id in user_team_ids