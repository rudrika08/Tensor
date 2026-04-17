import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, DateTime, Enum, JSON, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FLAGGED = "flagged"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Recommendation(str, enum.Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_MONITORING = "APPROVE_WITH_MONITORING"
    REFER_FOR_FIELD_VISIT = "REFER_FOR_FIELD_VISIT"
    REJECT = "REJECT"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Store metadata (optional, provided by submitter)
    store_name = Column(String(255), nullable=True)
    years_in_operation = Column(Integer, nullable=True)
    claimed_floor_area_sqft = Column(Float, nullable=True)
    monthly_rent = Column(Float, nullable=True)

    # Images: list of {path, label, blur_score, resolution, valid}
    image_records = Column(JSON, default=list)

    # Pipeline status
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    # Vision signals
    vision_signals = Column(JSON, nullable=True)

    # Geo signals
    geo_signals = Column(JSON, nullable=True)

    # Fraud assessment
    fraud_assessment = Column(JSON, nullable=True)

    # Cash flow estimate
    cash_flow_estimate = Column(JSON, nullable=True)

    # Final output
    recommendation = Column(Enum(Recommendation), nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    explanation = Column(Text, nullable=True)
    output_json = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "store_name": self.store_name,
            "years_in_operation": self.years_in_operation,
            "claimed_floor_area_sqft": self.claimed_floor_area_sqft,
            "monthly_rent": self.monthly_rent,
            "image_records": self.image_records,
            "status": self.status,
            "error_message": self.error_message,
            "vision_signals": self.vision_signals,
            "geo_signals": self.geo_signals,
            "fraud_assessment": self.fraud_assessment,
            "cash_flow_estimate": self.cash_flow_estimate,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "explanation": self.explanation,
        }
