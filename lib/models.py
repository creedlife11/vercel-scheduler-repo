"""
Pydantic models for API validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal
from datetime import date, datetime
import uuid

class LeaveEntry(BaseModel):
    Engineer: str = Field(..., min_length=1, max_length=50)
    Date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    Reason: str = Field(default="PTO", max_length=100)
    
    @validator('Date')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

class RotationSeeds(BaseModel):
    weekend: int = Field(default=0, ge=0, le=5)
    oncall: int = Field(default=0, ge=0, le=5)
    contacts: int = Field(default=0, ge=0, le=5)
    appointments: int = Field(default=0, ge=0, le=5)
    early: int = Field(default=0, ge=0, le=5)

class ScheduleRequest(BaseModel):
    engineers: List[str] = Field(..., min_items=6, max_items=6)
    start_sunday: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    weeks: int = Field(..., ge=1, le=52)
    seeds: RotationSeeds = Field(default_factory=RotationSeeds)
    leave: List[LeaveEntry] = Field(default_factory=list, max_items=100)
    format: Literal['csv', 'xlsx'] = Field(default='csv')
    random_seed: Optional[int] = Field(default=None, ge=0, le=2**31-1)
    
    @validator('engineers')
    def validate_engineers(cls, v):
        # Check for empty names
        for i, engineer in enumerate(v):
            if not engineer.strip():
                raise ValueError(f'Engineer {i+1} cannot be empty')
            if len(engineer.strip()) > 50:
                raise ValueError(f'Engineer {i+1} name too long (max 50 characters)')
        
        # Check for duplicates (case-insensitive)
        names_lower = [name.strip().lower() for name in v]
        if len(set(names_lower)) != len(names_lower):
            raise ValueError('Engineer names must be unique')
        
        return [name.strip() for name in v]
    
    @validator('start_sunday')
    def validate_start_sunday(cls, v):
        try:
            start_date = datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('start_sunday must be in YYYY-MM-DD format')
        
        if start_date.weekday() != 6:  # Sunday = 6
            raise ValueError('start_sunday must be a Sunday')
        
        # Check reasonable date range
        today = date.today()
        if start_date < today - timedelta(days=365):
            raise ValueError('start_sunday cannot be more than 1 year in the past')
        elif start_date > today + timedelta(days=730):
            raise ValueError('start_sunday cannot be more than 2 years in the future')
        
        return v
    
    @validator('leave')
    def validate_leave_engineers(cls, v, values):
        if 'engineers' not in values:
            return v
        
        valid_engineers = set(eng.strip().lower() for eng in values['engineers'])
        
        for entry in v:
            if entry.Engineer.strip().lower() not in valid_engineers:
                raise ValueError(f'Leave entry engineer "{entry.Engineer}" not in team')
        
        return v

class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[List[str]] = None
    requestId: str = Field(default_factory=lambda: str(uuid.uuid4()))

class ScheduleMetadata(BaseModel):
    requestId: str
    generatedAt: datetime
    inputSummary: Dict
    warnings: List[str] = Field(default_factory=list)
    processingTimeMs: float

class ScheduleResponse(BaseModel):
    data: List[Dict]
    metadata: ScheduleMetadata