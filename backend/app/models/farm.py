import uuid
from datetime import datetime, date, timezone
from typing import List, Optional
from sqlalchemy import (
    String,
    Float,
    Date,
    DateTime,
    CheckConstraint,
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("area_unit IN ('acres', 'hectares')", name="ck_farms_area_unit"),
        CheckConstraint("total_area > 0", name="ck_farms_total_area_positive"),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_farms_latitude"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_farms_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    farm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    total_area: Mapped[float] = mapped_column(Float, nullable=False)
    area_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="acres",
    )
    soil_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farmer: Mapped["User"] = relationship("User", back_populates="farms")
    crops: Mapped[List["FarmCrop"]] = relationship(
        "FarmCrop",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="FarmCrop.created_at",
    )
    weather_observations: Mapped[List["WeatherObservation"]] = relationship(
        "WeatherObservation",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="desc(WeatherObservation.observed_at)",
    )
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="desc(RiskAssessment.assessed_at)",
    )

    def __repr__(self) -> str:
        return f"<Farm id={self.id} name='{self.farm_name}' farmer_id={self.farmer_id}>"


class FarmCrop(Base):
    __tablename__ = "farm_crops"
    __table_args__ = (
        CheckConstraint("area_unit IN ('acres', 'hectares')", name="ck_crops_area_unit"),
        CheckConstraint("cultivated_area > 0", name="ck_crops_cultivated_area_positive"),
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
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cultivated_area: Mapped[float] = mapped_column(Float, nullable=False)
    area_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="acres",
    )
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="crops")

    def __repr__(self) -> str:
        return f"<FarmCrop id={self.id} crop='{self.crop_name}' farm_id={self.farm_id}>"

