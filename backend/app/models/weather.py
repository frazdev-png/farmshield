import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy import (
    String,
    Float,
    DateTime,
    ForeignKey,
    Uuid,
    JSON,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    __table_args__ = (
        Index("ix_weather_obs_farm_observed", "farm_id", "observed_at"),
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
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open-meteo",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precipitation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weather_condition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    forecast_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="weather_observations")
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="weather_observation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WeatherObservation id={self.id} farm_id={self.farm_id} temp={self.temperature} condition='{self.weather_condition}'>"

