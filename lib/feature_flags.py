"""
Feature flag system using Vercel Edge Config for gradual rollout capabilities.
Provides centralized feature toggle management with environment-specific configuration.
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import time
from functools import lru_cache


class FeatureFlagEnvironment(Enum):
    """Environment types for feature flag configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class FeatureFlag:
    """Individual feature flag configuration."""
    name: str
    enabled: bool
    rollout_percentage: int = 100  # 0-100
    environments: List[str] = None  # None means all environments
    user_groups: List[str] = None  # None means all users
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


class FeatureFlagManager:
    """
    Manages feature flags using Vercel Edge Config or local configuration.
    Supports gradual rollout, environment-specific flags, and user group targeting.
    """
    
    def __init__(self, environment: str = None):
        self.environment = environment or os.getenv("VERCEL_ENV", "development")
        self.edge_config_id = os.getenv("EDGE_CONFIG")
        self.edge_config_token = os.getenv("EDGE_CONFIG_TOKEN")
        self._cache_ttl = 300  # 5 minutes
        self._last_fetch = 0
        self._cached_flags: Dict[str, FeatureFlag] = {}
        
        # Load default flags
        self._load_default_flags()
    
    def _load_default_flags(self):
        """Load default feature flag configuration."""
        default_flags = {
            "enableFairnessReporting": FeatureFlag(
                name="enableFairnessReporting",
                enabled=True,
                rollout_percentage=100,
                description="Enable fairness analysis and reporting in schedule generation"
            ),
            "enableDecisionLogging": FeatureFlag(
                name="enableDecisionLogging", 
                enabled=True,
                rollout_percentage=100,
                description="Enable detailed decision logging during schedule generation"
            ),
            "enableAdvancedValidation": FeatureFlag(
                name="enableAdvancedValidation",
                enabled=True,
                rollout_percentage=100,
                description="Enable enhanced input validation with name hygiene"
            ),
            "enablePerformanceMonitoring": FeatureFlag(
                name="enablePerformanceMonitoring",
                enabled=True,
                rollout_percentage=100,
                description="Enable performance monitoring and metrics collection"
            ),
            "enableInvariantChecking": FeatureFlag(
                name="enableInvariantChecking",
                enabled=True,
                rollout_percentage=100,
                description="Enable scheduling invariant validation"
            ),
            "enableArtifactPanel": FeatureFlag(
                name="enableArtifactPanel",
                enabled=True,
                rollout_percentage=100,
                description="Enable enhanced artifact panel with multiple format tabs"
            ),
            "enableLeaveManagement": FeatureFlag(
                name="enableLeaveManagement",
                enabled=True,
                rollout_percentage=100,
                description="Enable leave management with CSV/XLSX import"
            ),
            "enablePresetManager": FeatureFlag(
                name="enablePresetManager",
                enabled=True,
                rollout_percentage=100,
                description="Enable preset configuration system"
            ),
            "enableAuthenticationSystem": FeatureFlag(
                name="enableAuthenticationSystem",
                enabled=True,
                rollout_percentage=100,
                environments=["staging", "production"],
                description="Enable authentication and authorization system"
            ),
            "enableRateLimiting": FeatureFlag(
                name="enableRateLimiting",
                enabled=True,
                rollout_percentage=100,
                environments=["staging", "production"],
                description="Enable request rate limiting and security controls"
            ),
            "enableTeamStorage": FeatureFlag(
                name="enableTeamStorage",
                enabled=True,
                rollout_percentage=50,
                environments=["staging", "production"],
                description="Enable team-scoped artifact storage (gradual rollout)"
            ),
            "maxWeeksAllowed": FeatureFlag(
                name="maxWeeksAllowed",
                enabled=True,
                rollout_percentage=100,
                description="Maximum weeks allowed in schedule generation (value stored separately)"
            ),
            "enableExperimentalFeatures": FeatureFlag(
                name="enableExperimentalFeatures",
                enabled=False,
                rollout_percentage=0,
                environments=["development"],
                description="Enable experimental features for testing"
            )
        }
        
        self._cached_flags = default_flags
    
    def is_enabled(self, flag_name: str, user_id: str = None, user_groups: List[str] = None) -> bool:
        """
        Check if a feature flag is enabled for the current context.
        
        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for user-specific rollouts
            user_groups: Optional user groups for group-based rollouts
            
        Returns:
            True if the feature is enabled, False otherwise
        """
        flag = self._get_flag(flag_name)
        if not flag:
            return False
        
        # Check if flag is globally disabled
        if not flag.enabled:
            return False
        
        # Check environment restrictions
        if flag.environments and self.environment not in flag.environments:
            return False
        
        # Check user group restrictions
        if flag.user_groups and user_groups:
            if not any(group in flag.user_groups for group in user_groups):
                return False
        
        # Check rollout percentage
        if flag.rollout_percentage < 100:
            # Use deterministic rollout based on user_id or flag name
            rollout_key = user_id or flag_name
            rollout_hash = hash(rollout_key) % 100
            if rollout_hash >= flag.rollout_percentage:
                return False
        
        return True
    
    def get_flag_value(self, flag_name: str, default_value: Any = None) -> Any:
        """
        Get the value of a feature flag (for flags that store values, not just boolean).
        
        Args:
            flag_name: Name of the feature flag
            default_value: Default value if flag is not found
            
        Returns:
            The flag value or default_value
        """
        # For value-based flags, we store the value in environment variables
        env_var_name = f"FEATURE_{flag_name.upper()}"
        env_value = os.getenv(env_var_name)
        
        if env_value is not None:
            # Try to parse as JSON first, then as string
            try:
                return json.loads(env_value)
            except json.JSONDecodeError:
                return env_value
        
        # Check if it's a special value flag
        if flag_name == "maxWeeksAllowed":
            return int(os.getenv("MAX_WEEKS_ALLOWED", "52"))
        elif flag_name == "fairnessThreshold":
            return float(os.getenv("FAIRNESS_THRESHOLD", "0.8"))
        elif flag_name == "maxRequestSizeMB":
            return float(os.getenv("MAX_REQUEST_SIZE_MB", "2.0"))
        
        return default_value
    
    def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags with their current status."""
        self._refresh_flags_if_needed()
        return self._cached_flags.copy()
    
    def _get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a specific feature flag."""
        self._refresh_flags_if_needed()
        return self._cached_flags.get(flag_name)
    
    def _refresh_flags_if_needed(self):
        """Refresh flags from Edge Config if cache is stale."""
        current_time = time.time()
        if current_time - self._last_fetch > self._cache_ttl:
            self._fetch_flags_from_edge_config()
            self._last_fetch = current_time
    
    def _fetch_flags_from_edge_config(self):
        """Fetch feature flags from Vercel Edge Config."""
        if not self.edge_config_id or not self.edge_config_token:
            # No Edge Config configured, use defaults
            return
        
        try:
            url = f"https://edge-config.vercel.com/{self.edge_config_id}/items"
            headers = {
                "Authorization": f"Bearer {self.edge_config_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            edge_config_data = response.json()
            
            # Update cached flags with Edge Config data
            for flag_name, flag_data in edge_config_data.items():
                if isinstance(flag_data, dict) and "enabled" in flag_data:
                    self._cached_flags[flag_name] = FeatureFlag(
                        name=flag_name,
                        enabled=flag_data.get("enabled", False),
                        rollout_percentage=flag_data.get("rollout_percentage", 100),
                        environments=flag_data.get("environments"),
                        user_groups=flag_data.get("user_groups"),
                        description=flag_data.get("description", ""),
                        created_at=flag_data.get("created_at", ""),
                        updated_at=flag_data.get("updated_at", "")
                    )
        
        except Exception as e:
            # Log error but don't fail - use cached/default flags
            print(f"Warning: Failed to fetch feature flags from Edge Config: {e}")
    
    @lru_cache(maxsize=128)
    def get_feature_config(self) -> Dict[str, Any]:
        """
        Get complete feature configuration for frontend.
        Cached to avoid repeated computation.
        """
        config = {}
        
        for flag_name, flag in self._cached_flags.items():
            config[flag_name] = {
                "enabled": self.is_enabled(flag_name),
                "rollout_percentage": flag.rollout_percentage,
                "description": flag.description
            }
        
        # Add value-based configurations
        config["maxWeeksAllowed"] = self.get_flag_value("maxWeeksAllowed", 52)
        config["fairnessThreshold"] = self.get_flag_value("fairnessThreshold", 0.8)
        config["maxRequestSizeMB"] = self.get_flag_value("maxRequestSizeMB", 2.0)
        
        return config


# Global feature flag manager instance
feature_flags = FeatureFlagManager()


# Convenience functions for common feature checks
def is_fairness_reporting_enabled(user_id: str = None) -> bool:
    """Check if fairness reporting is enabled."""
    return feature_flags.is_enabled("enableFairnessReporting", user_id)


def is_decision_logging_enabled(user_id: str = None) -> bool:
    """Check if decision logging is enabled."""
    return feature_flags.is_enabled("enableDecisionLogging", user_id)


def is_advanced_validation_enabled(user_id: str = None) -> bool:
    """Check if advanced validation is enabled."""
    return feature_flags.is_enabled("enableAdvancedValidation", user_id)


def is_performance_monitoring_enabled(user_id: str = None) -> bool:
    """Check if performance monitoring is enabled."""
    return feature_flags.is_enabled("enablePerformanceMonitoring", user_id)


def is_authentication_enabled(user_id: str = None) -> bool:
    """Check if authentication system is enabled."""
    return feature_flags.is_enabled("enableAuthenticationSystem", user_id)


def get_max_weeks_allowed() -> int:
    """Get the maximum weeks allowed for schedule generation."""
    return feature_flags.get_flag_value("maxWeeksAllowed", 52)


def get_fairness_threshold() -> float:
    """Get the fairness threshold for equity scoring."""
    return feature_flags.get_flag_value("fairnessThreshold", 0.8)