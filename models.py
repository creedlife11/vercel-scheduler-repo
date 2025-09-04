"""
Enhanced data models for the scheduler with strict validation.
Implements ScheduleResult, FairnessReport, and DecisionEntry dataclasses
along with Pydantic models for API validation.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator, root_validator
import re
import unicodedata
import sys
import os

# Add lib directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

try:
    from name_hygiene import (
        normalize_name, 
        validate_name_characters, 
        validate_engineer_list,
        calculate_name_similarity
    )
except ImportError:
    # Fallback implementations if name_hygiene module is not available
    def normalize_name(name: str) -> str:
        return re.sub(r'\s+', ' ', name.strip()) if name else ""
    
    def validate_name_characters(name: str) -> bool:
        return bool(re.match(r"^[a-zA-ZÀ-ÿ\s\-'\.]+$", name.strip())) if name else False
    
    def validate_engineer_list(names):
        return {"is_valid": True, "errors": [], "warnings": [], "normalized_names": names}
    
    def calculate_name_similarity(name1: str, name2: str) -> float:
        return 1.0 if name1.lower() == name2.lower() else 0.0


# Core Data Models (dataclasses)

@dataclass
class EngineerStats:
    """Statistics for a single engineer's role assignments."""
    name: str
    oncall_count: int = 0
    weekend_count: int = 0
    early_count: int = 0
    chat_count: int = 0
    appointments_count: int = 0
    total_work_days: int = 0
    leave_days: int = 0


@dataclass
class FairnessReport:
    """Comprehensive fairness analysis for schedule distribution."""
    engineer_stats: Dict[str, EngineerStats]
    equity_score: float  # Gini coefficient (0 = perfect equality, 1 = maximum inequality)
    max_min_deltas: Dict[str, int]  # Max - Min for each role type
    generation_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionEntry:
    """Log entry for scheduling decisions and rationale."""
    date: str
    decision_type: str  # "role_assignment", "leave_conflict", "backfill", etc.
    affected_engineers: List[str]
    reason: str
    alternatives_considered: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScheduleMetadata:
    """Metadata about schedule generation."""
    generation_timestamp: datetime
    configuration: Dict[str, Any]
    engineer_count: int
    weeks: int
    start_date: date
    end_date: date
    total_days: int


@dataclass
class WeekendCompensation:
    """Track compensatory time off for weekend workers."""
    engineer: str
    weekend_date: date
    compensation_dates: List[date]
    pattern_type: str  # 'A' or 'B'


@dataclass
class ScheduleResult:
    """Complete schedule result with all associated data."""
    schedule_data: Dict[str, Any]
    fairness_report: FairnessReport
    decision_log: List[DecisionEntry]
    metadata: ScheduleMetadata
    weekend_compensation_tracking: List[WeekendCompensation] = field(default_factory=list)
    fairness_insights: List[str] = field(default_factory=list)
    schema_version: str = "2.0"


# Pydantic Models for API Validation

# Use the enhanced name hygiene functions
normalize_engineer_name = normalize_name
validate_engineer_name_format = validate_name_characters


class ValidationError(BaseModel):
    """Structured validation error for API responses."""
    field: str
    message: str
    code: str
    value: Optional[Any] = None


class APIErrorResponse(BaseModel):
    """Standardized API error response."""
    error: str
    details: List[ValidationError] = Field(default_factory=list)
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class LeaveEntry(BaseModel):
    """Individual leave entry with validation."""
    engineer: str = Field(..., min_length=1, max_length=100)
    date: date
    reason: str = Field(default="", max_length=200)

    @validator('engineer')
    def validate_engineer_name(cls, v):
        """Validate and normalize engineer name."""
        v = normalize_engineer_name(v)
        if not v:
            raise ValueError("Engineer name cannot be empty after normalization")
        
        if not validate_engineer_name_format(v):
            raise ValueError("Engineer name contains invalid characters. Use only letters, spaces, hyphens, apostrophes, and periods")
        
        if len(v) > 100:
            raise ValueError("Engineer name is too long (maximum 100 characters)")
            
        return v


class SeedsConfig(BaseModel):
    """Seed configuration for role rotation."""
    weekend: int = Field(default=0, ge=0, le=5)
    chat: int = Field(default=0, ge=0, le=5)
    oncall: int = Field(default=1, ge=0, le=5)
    appointments: int = Field(default=2, ge=0, le=5)
    early: int = Field(default=0, ge=0, le=5)


class ScheduleRequest(BaseModel):
    """Complete schedule generation request with validation."""
    engineers: List[str] = Field(..., min_items=6, max_items=6)
    start_sunday: date
    weeks: int = Field(..., ge=1, le=52)
    seeds: SeedsConfig = Field(default_factory=SeedsConfig)
    leave: List[LeaveEntry] = Field(default_factory=list)
    format: Literal['csv', 'xlsx', 'json'] = 'csv'
    
    @validator('engineers')
    def validate_unique_engineers(cls, v):
        """Ensure engineer names are unique and properly formatted using enhanced validation."""
        if not v:
            raise ValueError("Engineers list cannot be empty")
        
        # Use the comprehensive validation from name_hygiene module
        validation_result = validate_engineer_list(v)
        
        if not validation_result["is_valid"]:
            # Combine all errors into a single message
            error_msg = "; ".join(validation_result["errors"])
            raise ValueError(error_msg)
        
        # Log warnings if any (in a real system, you'd use proper logging)
        if validation_result["warnings"]:
            # For now, we'll include warnings in a way that doesn't fail validation
            # In production, you might want to log these or return them separately
            pass
        
        return validation_result["normalized_names"]
    
    @validator('start_sunday')
    def validate_sunday_start(cls, v):
        """Ensure start date is a Sunday."""
        if v.weekday() != 6:  # Sunday = 6 in Python
            raise ValueError("Start date must be a Sunday")
        return v
    
    @validator('leave')
    def validate_leave_entries(cls, v, values):
        """Validate leave entries against engineer list."""
        if 'engineers' not in values:
            return v
        
        engineer_names = {name.lower() for name in values['engineers']}
        
        for entry in v:
            if entry.engineer.lower() not in engineer_names:
                raise ValueError(f"Leave entry for unknown engineer: '{entry.engineer}'")
        
        return v


class ScheduleRow(BaseModel):
    """Individual schedule row with validation."""
    date: date
    day: str
    week_index: int = Field(ge=0)
    early1: str = ""
    early2: str = ""
    chat: str = ""
    oncall: str = ""
    appointments: str = ""
    engineers: List['EngineerStatus']

    @validator('day')
    def validate_day_format(cls, v):
        """Ensure day is in correct 3-letter format."""
        valid_days = {'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'}
        if v not in valid_days:
            raise ValueError(f"Invalid day format: '{v}'. Must be one of {valid_days}")
        return v


class EngineerStatus(BaseModel):
    """Engineer status for a specific day with validation."""
    name: str = Field(..., min_length=1)
    status: Literal["WORK", "OFF", "LEAVE", ""] = ""
    shift: str = ""
    
    @validator('status')
    def validate_status_not_engineer_name(cls, v, values):
        """Ensure status field doesn't contain engineer name."""
        if 'name' in values and v == values['name']:
            raise ValueError("Status field cannot equal engineer name")
        return v
    
    @validator('shift')
    def validate_shift_format(cls, v, values):
        """Validate shift time format."""
        if not v:
            return v
        
        # Allow common shift patterns
        valid_patterns = [
            r'^\d{2}:\d{2}-\d{2}:\d{2}$',  # HH:MM-HH:MM
            r'^Weekend$',
            r'^$'  # Empty string
        ]
        
        if not any(re.match(pattern, v) for pattern in valid_patterns):
            raise ValueError(f"Invalid shift format: '{v}'")
        
        return v


# Update forward references
ScheduleRow.update_forward_refs()