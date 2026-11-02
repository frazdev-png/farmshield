import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_admin, require_farmer
from app.models.user import User
from app.models.notification import Notification, BroadcastAudit
from app.schemas.notification import (
    FarmerPreferenceResponse,
    FarmerPreferenceUpdate,
    NotificationResponse,
    NotificationListResponse,
    MarkReadResponse,
    MarkAllReadResponse,
    AdminBroadcastRequest,
    AdminBroadcastPreviewResponse,
    AdminBroadcastResponse,
    BroadcastAuditResponse,
)
from app.services.notification.service import NotificationService

router = APIRouter()
admin_router = APIRouter()


# ---------------------------------------------------------
# Farmer Notification Endpoints
# ---------------------------------------------------------

@router.get("/preferences", response_model=FarmerPreferenceResponse)
def get_preferences(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Retrieves current farmer's notification and SMS consent preferences."""
    service = NotificationService(db)
    pref = service.get_farmer_preference(current_user.id)
    return pref


@router.patch("/preferences", response_model=FarmerPreferenceResponse)
def update_preferences(
    payload: FarmerPreferenceUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Updates SMS consent and language preferences with explicit audit timestamp."""
    service = NotificationService(db)
    updated = service.update_farmer_preference(
        user_id=current_user.id,
        sms_consent=payload.sms_consent,
        language_preference=payload.language_preference,
    )
    return updated


@router.get("", response_model=NotificationListResponse)
def list_farmer_notifications(
    farm_id: Optional[uuid.UUID] = Query(None, description="Filter notifications by farm ID"),
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Lists notifications for the authenticated farmer with pagination."""
    service = NotificationService(db)
    items, total = service.list_farmer_notifications(
        farmer_id=current_user.id,
        farm_id=farm_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    _, unread_total = service.list_farmer_notifications(
        farmer_id=current_user.id,
        unread_only=True,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_total,
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_farmer_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Retrieves a single notification owned by the current farmer."""
    service = NotificationService(db)
    notification = service.get_notification(current_user.id, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return notification


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Marks a single notification as read."""
    service = NotificationService(db)
    notification = service.mark_as_read(current_user.id, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return MarkReadResponse(
        success=True,
        message="Notification marked as read.",
        notification=NotificationResponse.model_validate(notification),
    )


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
def mark_all_notifications_as_read(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Marks all unread notifications for the current farmer as read."""
    service = NotificationService(db)
    count = service.mark_all_as_read(current_user.id)
    return MarkAllReadResponse(
        success=True,
        marked_count=count,
    )


@router.post("/simulate-alert", response_model=NotificationResponse)
def simulate_hazard_alert_and_sms(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """
    Simulates a high-priority agro-climatic hazard alert and triggers immediate AWS SNS SMS dispatch 
    to the farmer's registered phone number with exact timestamp audit.
    """
    from datetime import datetime, timezone
    from app.models.farm import Farm
    from app.services.notification.sns_provider import SNSProvider, mask_phone_number

    # 1. Fetch user's farm
    farm = db.scalar(
        select(Farm)
        .where(Farm.farmer_id == current_user.id)
        .order_by(Farm.created_at.desc())
    )
    if not farm and current_user.role == "admin":
        farm = db.scalar(select(Farm).order_by(Farm.created_at.desc()))

    farm_name = farm.farm_name if farm else "Green Acres Farm"
    district = farm.district if farm else "Multan"
    now_utc = datetime.now(timezone.utc)

    # 2. Craft high-priority alert message
    alert_title = "⚡ Frost & Sudden Temperature Drop Alert"
    alert_msg = (
        f"FarmShield Advisory for {farm_name} ({district}): Night temperatures expected to drop rapidly to 3.5°C. "
        f"High frost risk detected. Apply light evening irrigation to protect root zones and shield young nurseries."
    )

    phone = current_user.phone_number or "+923116310515"
    masked_phone = mask_phone_number(phone)

    # 3. Dispatch SMS via AWS SNS provider
    sns = SNSProvider()
    sms_res = sns.send_sms(phone, alert_msg)

    # 4. Create and persist Notification
    notif = Notification(
        farmer_id=current_user.id,
        farm_id=farm.id if farm else None,
        notification_type="hazard_alert",
        title=alert_title,
        message=alert_msg,
        severity="HIGH",
        channel="both",
        is_read=False,
        status=sms_res.get("status", "accepted"),
        sns_message_id=sms_res.get("message_id") or f"sim-{uuid.uuid4().hex[:12]}",
        masked_phone_number=masked_phone,
        delivery_attempts=1,
        last_attempt_at=now_utc,
        error_message=sms_res.get("error"),
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


# ---------------------------------------------------------
# Admin Notification Endpoints
# ---------------------------------------------------------

@admin_router.get("", response_model=NotificationListResponse)
def list_admin_notifications(
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, CRITICAL)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by delivery status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: query all notifications across all farmers with masked phone numbers."""
    service = NotificationService(db)
    items, total = service.list_admin_notifications(
        severity=severity,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=0,
    )


@admin_router.get("/{notification_id}", response_model=NotificationResponse)
def get_admin_notification(
    notification_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: view details of any notification."""
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return notification


@admin_router.post("/broadcast/preview", response_model=AdminBroadcastPreviewResponse)
def preview_emergency_broadcast(
    payload: AdminBroadcastRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only dry run preview: inspect targeted farmers and SMS consent count before dispatch."""
    service = NotificationService(db)
    preview = service.preview_admin_broadcast(
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        district=payload.district,
    )
    return AdminBroadcastPreviewResponse(**preview)


@admin_router.post("/broadcast", response_model=AdminBroadcastResponse)
def broadcast_emergency_advisory(
    payload: AdminBroadcastRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: dispatch an emergency broadcast advisory to farmers with SMS integration."""
    if not payload.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broadcast execution requires explicit confirmation. Set confirmed=true in request payload.",
        )

    service = NotificationService(db)
    result = service.admin_broadcast(
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        district=payload.district,
        admin_id=current_admin.id,
        confirmed=True,
    )
    return AdminBroadcastResponse(
        audit_id=result.get("audit_id"),
        target_farmers_count=result["target_farmers_count"],
        notifications_queued=result["notifications_queued"],
        sms_accepted_count=result["sms_accepted_count"],
        sms_skipped_or_failed_count=result["sms_skipped_or_failed_count"],
        message=f"Broadcast advisory dispatched to {result['target_farmers_count']} farmers ({result['sms_accepted_count']} SMS dispatches accepted).",
    )


@admin_router.post("/retry", response_model=NotificationListResponse)
def retry_transient_sms_notifications(
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: triggers bounded retry of pending or transiently failed SMS notifications."""
    service = NotificationService(db)
    retried = service.retry_failed_notifications(limit=limit)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in retried],
        total=len(retried),
        unread_count=0,
    )


@admin_router.get("/audits", response_model=List[BroadcastAuditResponse])
def list_broadcast_audits(
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: lists historical emergency broadcast dispatch audit records."""
    stmt = (
        select(BroadcastAudit)
        .order_by(desc(BroadcastAudit.created_at))
        .limit(limit)
    )
    audits = list(db.scalars(stmt).all())
    return [BroadcastAuditResponse.model_validate(a) for a in audits]

