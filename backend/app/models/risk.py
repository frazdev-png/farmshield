import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    String,
    Float,
    DateTime,
    ForeignKey,
    Uuid,
    JSON,
    Text,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')",
            name="ck_risk_level_valid",
        ),
        CheckConstraint(
            "risk_score >= 0.0 AND risk_score <= 100.0",
            name="ck_risk_score_range",
        ),
        Index("ix_risk_assessments_farm_assessed", "farm_id", "assessed_at"),
        Index("ix_risk_assessments_farm_category", "farm_id", "risk_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weather_observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("weather_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_category: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[Any] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_precaution: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="risk_assessments")
    weather_observation: Mapped[Optional["WeatherObservation"]] = relationship(
        "WeatherObservation",
        back_populates="risk_assessments",
    )

    def __repr__(self) -> str:
        return f"<RiskAssessment id={self.id} farm_id={self.farm_id} cat='{self.risk_category}' lvl='{self.risk_level}' score={self.risk_score}>"

