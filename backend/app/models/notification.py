import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Uuid,
    Text,
    Integer,
    CheckConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.farm import Farm
    from app.models.risk import RiskAssessment


class FarmerPreference(Base):
    __tablename__ = "farmer_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    sms_consent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    sms_consent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    language_preference: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )
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

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<FarmerPreference user_id={self.user_id} sms_consent={self.sms_consent}>"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')",
            name="ck_notifications_severity_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'sending', 'accepted', 'delivered', 'failed')",
            name="ck_notifications_status_valid",
        ),
        CheckConstraint(
            "channel IN ('in_app', 'sms', 'both')",
            name="ck_notifications_channel_valid",
        ),
        Index("ix_notifications_farmer_created", "farmer_id", "created_at"),
        UniqueConstraint("farm_id", "risk_assessment_id", name="uq_notifications_farm_risk_assessment"),
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
    farm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    risk_assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="risk_alert",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="LOW",
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_app",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    sns_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    masked_phone_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    delivery_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
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
    farmer: Mapped["User"] = relationship("User", back_populates="notifications")
    farm: Mapped[Optional["Farm"]] = relationship("Farm")
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship("RiskAssessment")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} farmer_id={self.farmer_id} severity='{self.severity}' status='{self.status}'>"


class BroadcastAudit(Base):
    __tablename__ = "broadcast_audits"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_farmers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sms_consented_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notifications_queued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sms_accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sms_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    admin: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<BroadcastAudit id={self.id} title='{self.title}' target={self.target_farmers_count} accepted={self.sms_accepted_count}>"


