from pydantic import BaseModel, Field, validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ImageRecord(BaseModel):
    path: str
    label: str  # shelf | counter | exterior | unknown
    blur_score: float
    resolution: tuple
    valid: bool
    exif_timestamp: Optional[str] = None


class SubmissionCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    store_name: Optional[str] = None
    years_in_operation: Optional[int] = Field(None, ge=0, le=200)
    claimed_floor_area_sqft: Optional[float] = Field(None, ge=0)
    monthly_rent: Optional[float] = Field(None, ge=0)


class SubmissionResponse(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    latitude: float
    longitude: float
    store_name: Optional[str]
    image_count: int
    message: str

    class Config:
        from_attributes = True


class SubmissionDetail(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    status: str
    latitude: float
    longitude: float
    store_name: Optional[str]
    years_in_operation: Optional[int]
    claimed_floor_area_sqft: Optional[float]
    monthly_rent: Optional[float]
    image_records: Optional[List[dict]]
    vision_signals: Optional[dict]
    geo_signals: Optional[dict]
    fraud_assessment: Optional[dict]
    cash_flow_estimate: Optional[dict]
    recommendation: Optional[str]
    risk_level: Optional[str]
    explanation: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class SubmissionListItem(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    store_name: Optional[str]
    latitude: float
    longitude: float
    recommendation: Optional[str]
    risk_level: Optional[str]

    class Config:
        from_attributes = True
