import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class FarmerPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    sms_consent: bool
    sms_consent_at: Optional[datetime] = None
    language_preference: str = "en"
    updated_at: datetime


class FarmerPreferenceUpdate(BaseModel):
    sms_consent: bool = Field(..., description="Consent to receive urgent agricultural SMS alerts")
    language_preference: Optional[str] = Field("en", description="Language preference ('en', 'ur', etc.)")


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: Optional[uuid.UUID] = None
    risk_assessment_id: Optional[uuid.UUID] = None
    notification_type: str
    title: str
    message: str
    severity: str
    channel: str
    is_read: bool
    status: str
    sns_message_id: Optional[str] = None
    masked_phone_number: Optional[str] = None
    delivery_attempts: int
    last_attempt_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool
    message: str
    notification: Optional[NotificationResponse] = None


class MarkAllReadResponse(BaseModel):
    success: bool
    marked_count: int


class AdminBroadcastRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5, max_length=1000)
    severity: str = Field("HIGH", pattern="^(LOW|MODERATE|HIGH|CRITICAL)$")
    district: Optional[str] = Field(None, description="Optional target district or 'all'")
    confirmed: bool = Field(False, description="Explicit confirmation required to execute broadcast")


class AdminBroadcastPreviewResponse(BaseModel):
    target_farmers_count: int
    sms_consented_count: int
    in_app_only_count: int
    district: Optional[str] = None
    severity: str
    title: str
    message: str


class AdminBroadcastResponse(BaseModel):
    audit_id: Optional[uuid.UUID] = None
    target_farmers_count: int
    notifications_queued: int
    sms_accepted_count: int
    sms_skipped_or_failed_count: int
    message: str


class BroadcastAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_id: Optional[uuid.UUID] = None
    title: str
    message: str
    severity: str
    district: Optional[str] = None
    target_farmers_count: int
    sms_consented_count: int
    notifications_queued: int
    sms_accepted_count: int
    sms_failed_count: int
    created_at: datetime

