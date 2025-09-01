"""
Environment-specific configuration management for the scheduler application.
Handles different settings for development, staging, and production environments.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    PREVIEW = "preview"  # Vercel preview deployments
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: Optional[str] = None
    max_connections: int = 10
    connection_timeout: int = 30
    ssl_mode: str = "prefer"


@dataclass
class AuthConfig:
    """Authentication configuration settings."""
    enabled: bool = True
    provider: str = "nextauth"  # "nextauth" or "clerk"
    session_max_age: int = 86400  # 24 hours
    jwt_secret: Optional[str] = None
    allowed_domains: Optional[list] = None


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_hour: int = 100
    requests_per_minute: int = 10
    burst_limit: int = 20
    window_size_seconds: int = 3600


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration."""
    log_level: str = "INFO"
    structured_logging: bool = True
    performance_monitoring: bool = True
    error_tracking: bool = True
    metrics_endpoint: bool = False


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    max_request_size_mb: float = 2.0
    max_weeks_allowed: int = 52
    max_engineers: int = 20
    cors_origins: list = None
    csrf_protection: bool = True


@dataclass
class FeatureConfig:
    """Feature-specific configuration."""
    fairness_threshold: float = 0.8
    enable_team_storage: bool = True
    enable_artifact_sharing: bool = True
    enable_preset_sharing: bool = True
    cache_ttl_seconds: int = 300


@dataclass
class AppConfig:
    """Complete application configuration."""
    environment: Environment
    debug: bool = False
    database: DatabaseConfig = None
    auth: AuthConfig = None
    rate_limiting: RateLimitConfig = None
    monitoring: MonitoringConfig = None
    security: SecurityConfig = None
    features: FeatureConfig = None
    
    def __post_init__(self):
        """Initialize default configurations if not provided."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.auth is None:
            self.auth = AuthConfig()
        if self.rate_limiting is None:
            self.rate_limiting = RateLimitConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.features is None:
            self.features = FeatureConfig()


class ConfigManager:
    """
    Manages environment-specific configuration for the application.
    Loads configuration from environment variables and provides defaults.
    """
    
    def __init__(self):
        self.environment = self._detect_environment()
        self._config_cache: Optional[AppConfig] = None
    
    def get_config(self) -> AppConfig:
        """Get the complete application configuration."""
        if self._config_cache is None:
            self._config_cache = self._load_config()
        return self._config_cache
    
    def _detect_environment(self) -> Environment:
        """Detect the current deployment environment."""
        vercel_env = os.getenv("VERCEL_ENV", "development")
        
        if vercel_env == "production":
            return Environment.PRODUCTION
        elif vercel_env == "preview":
            return Environment.PREVIEW
        else:
            return Environment.DEVELOPMENT
    
    def _load_config(self) -> AppConfig:
        """Load configuration based on the current environment."""
        if self.environment == Environment.PRODUCTION:
            return self._load_production_config()
        elif self.environment == Environment.PREVIEW:
            return self._load_preview_config()
        else:
            return self._load_development_config()
    
    def _load_development_config(self) -> AppConfig:
        """Load development environment configuration."""
        return AppConfig(
            environment=Environment.DEVELOPMENT,
            debug=True,
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL"),
                max_connections=5,
                connection_timeout=10
            ),
            auth=AuthConfig(
                enabled=os.getenv("ENABLE_AUTH", "false").lower() == "true",
                provider=os.getenv("AUTH_PROVIDER", "nextauth"),
                session_max_age=3600,  # 1 hour for dev
                jwt_secret=os.getenv("NEXTAUTH_SECRET"),
                allowed_domains=self._parse_list_env("ALLOWED_DOMAINS")
            ),
            rate_limiting=RateLimitConfig(
                enabled=False,  # Disabled in development
                requests_per_hour=1000,
                requests_per_minute=100
            ),
            monitoring=MonitoringConfig(
                log_level=os.getenv("LOG_LEVEL", "DEBUG"),
                structured_logging=True,
                performance_monitoring=True,
                error_tracking=False,  # Disabled in dev
                metrics_endpoint=True
            ),
            security=SecurityConfig(
                max_request_size_mb=float(os.getenv("MAX_REQUEST_SIZE_MB", "5.0")),
                max_weeks_allowed=int(os.getenv("MAX_WEEKS_ALLOWED", "104")),  # More lenient in dev
                max_engineers=int(os.getenv("MAX_ENGINEERS", "50")),
                cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                csrf_protection=False  # Disabled for easier testing
            ),
            features=FeatureConfig(
                fairness_threshold=float(os.getenv("FAIRNESS_THRESHOLD", "0.5")),
                enable_team_storage=True,
                enable_artifact_sharing=True,
                enable_preset_sharing=True,
                cache_ttl_seconds=60  # Shorter cache in dev
            )
        )
    
    def _load_preview_config(self) -> AppConfig:
        """Load preview/staging environment configuration."""
        return AppConfig(
            environment=Environment.PREVIEW,
            debug=False,
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL"),
                max_connections=10,
                connection_timeout=20,
                ssl_mode="require"
            ),
            auth=AuthConfig(
                enabled=True,
                provider=os.getenv("AUTH_PROVIDER", "nextauth"),
                session_max_age=43200,  # 12 hours
                jwt_secret=os.getenv("NEXTAUTH_SECRET"),
                allowed_domains=self._parse_list_env("ALLOWED_DOMAINS")
            ),
            rate_limiting=RateLimitConfig(
                enabled=True,
                requests_per_hour=200,
                requests_per_minute=20,
                burst_limit=30
            ),
            monitoring=MonitoringConfig(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                structured_logging=True,
                performance_monitoring=True,
                error_tracking=True,
                metrics_endpoint=True
            ),
            security=SecurityConfig(
                max_request_size_mb=float(os.getenv("MAX_REQUEST_SIZE_MB", "3.0")),
                max_weeks_allowed=int(os.getenv("MAX_WEEKS_ALLOWED", "52")),
                max_engineers=int(os.getenv("MAX_ENGINEERS", "20")),
                cors_origins=self._parse_list_env("CORS_ORIGINS"),
                csrf_protection=True
            ),
            features=FeatureConfig(
                fairness_threshold=float(os.getenv("FAIRNESS_THRESHOLD", "0.7")),
                enable_team_storage=True,
                enable_artifact_sharing=True,
                enable_preset_sharing=True,
                cache_ttl_seconds=300
            )
        )
    
    def _load_production_config(self) -> AppConfig:
        """Load production environment configuration."""
        return AppConfig(
            environment=Environment.PRODUCTION,
            debug=False,
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL"),
                max_connections=20,
                connection_timeout=30,
                ssl_mode="require"
            ),
            auth=AuthConfig(
                enabled=True,
                provider=os.getenv("AUTH_PROVIDER", "nextauth"),
                session_max_age=86400,  # 24 hours
                jwt_secret=os.getenv("NEXTAUTH_SECRET"),
                allowed_domains=self._parse_list_env("ALLOWED_DOMAINS")
            ),
            rate_limiting=RateLimitConfig(
                enabled=True,
                requests_per_hour=int(os.getenv("RATE_LIMIT_HOUR", "100")),
                requests_per_minute=int(os.getenv("RATE_LIMIT_MINUTE", "10")),
                burst_limit=int(os.getenv("RATE_LIMIT_BURST", "20"))
            ),
            monitoring=MonitoringConfig(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                structured_logging=True,
                performance_monitoring=True,
                error_tracking=True,
                metrics_endpoint=os.getenv("ENABLE_METRICS", "false").lower() == "true"
            ),
            security=SecurityConfig(
                max_request_size_mb=float(os.getenv("MAX_REQUEST_SIZE_MB", "2.0")),
                max_weeks_allowed=int(os.getenv("MAX_WEEKS_ALLOWED", "52")),
                max_engineers=int(os.getenv("MAX_ENGINEERS", "10")),
                cors_origins=self._parse_list_env("CORS_ORIGINS"),
                csrf_protection=True
            ),
            features=FeatureConfig(
                fairness_threshold=float(os.getenv("FAIRNESS_THRESHOLD", "0.8")),
                enable_team_storage=True,
                enable_artifact_sharing=os.getenv("ENABLE_ARTIFACT_SHARING", "true").lower() == "true",
                enable_preset_sharing=os.getenv("ENABLE_PRESET_SHARING", "true").lower() == "true",
                cache_ttl_seconds=int(os.getenv("CACHE_TTL", "600"))  # 10 minutes
            )
        )
    
    def _parse_list_env(self, env_var: str) -> Optional[list]:
        """Parse a comma-separated environment variable into a list."""
        value = os.getenv(env_var)
        if not value:
            return None
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def get_database_url(self) -> Optional[str]:
        """Get the database URL for the current environment."""
        return self.get_config().database.url
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_config().debug
    
    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.get_config().auth.enabled
    
    def get_max_weeks_allowed(self) -> int:
        """Get the maximum weeks allowed for schedule generation."""
        return self.get_config().security.max_weeks_allowed
    
    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limiting configuration."""
        return self.get_config().rate_limiting
    
    def export_config_json(self) -> str:
        """Export configuration as JSON for debugging."""
        config = self.get_config()
        # Remove sensitive data
        config_dict = asdict(config)
        if config_dict.get("auth", {}).get("jwt_secret"):
            config_dict["auth"]["jwt_secret"] = "***REDACTED***"
        if config_dict.get("database", {}).get("url"):
            config_dict["database"]["url"] = "***REDACTED***"
        
        return json.dumps(config_dict, indent=2, default=str)


# Global configuration manager instance
config_manager = ConfigManager()


# Convenience functions for common configuration access
def get_config() -> AppConfig:
    """Get the complete application configuration."""
    return config_manager.get_config()


def get_environment() -> Environment:
    """Get the current environment."""
    return config_manager.environment


def is_production() -> bool:
    """Check if running in production environment."""
    return config_manager.environment == Environment.PRODUCTION


def is_development() -> bool:
    """Check if running in development environment."""
    return config_manager.environment == Environment.DEVELOPMENT