import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.models.risk import RiskAssessment
from app.models.conversation import Conversation, ConversationMessage
from app.models.notification import Notification
from app.services.notification.sns_provider import mask_phone_number
from app.schemas.admin import (
    AdminOverviewStats,
    AdminFarmerItem,
    AdminRiskMonitoringItem,
    AdminAgentActivityItem,
    FarmerStatusUpdateRequest,
    FarmerActionResponse,
)

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewStats)
def get_admin_overview_stats(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Real aggregated database metrics across agricultural operations."""
    total_farmers = db.scalar(
        select(func.count()).select_from(User).where(User.role == "farmer")
    ) or 0

    total_farms = db.scalar(
        select(func.count()).select_from(Farm)
    ) or 0

    total_monitored_acres = db.scalar(
        select(func.coalesce(func.sum(Farm.total_area), 0.0))
    ) or 0.0

    active_threats_count = db.scalar(
        select(func.count())
        .select_from(RiskAssessment)
        .where(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"]))
    ) or 0

    total_ai_queries_count = db.scalar(
        select(func.count())
        .select_from(ConversationMessage)
        .where(ConversationMessage.sender == "user")
    ) or 0

    total_notifications_count = db.scalar(
        select(func.count()).select_from(Notification)
    ) or 0

    return AdminOverviewStats(
        total_farmers=total_farmers,
        total_farms=total_farms,
        total_monitored_acres=round(float(total_monitored_acres), 1),
        active_threats_count=active_threats_count,
        total_ai_queries_count=total_ai_queries_count,
        total_notifications_count=total_notifications_count,
        system_status="OPERATIONAL",
    )


@router.get("/farmers", response_model=List[AdminFarmerItem])
def list_admin_farmers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Retrieve real enrolled farmers with aggregated acreage, crops, and risk tier."""
    stmt = (
        select(User)
        .where(User.role == "farmer")
        .options(
            selectinload(User.farms).selectinload(Farm.crops),
            selectinload(User.farms).selectinload(Farm.risk_assessments),
        )
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(limit)
    )
    farmers = list(db.scalars(stmt).all())

    result: List[AdminFarmerItem] = []
    for f in farmers:
        farms_count = len(f.farms)
        total_acres = sum(farm.total_area for farm in f.farms)

        crop_names: set = set()
        highest_risk = "LOW"
        risk_priority = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}

        for farm in f.farms:
            for crop in farm.crops:
                crop_names.add(crop.crop_name)
            for ra in farm.risk_assessments:
                if risk_priority.get(ra.risk_level, 0) > risk_priority.get(highest_risk, 0):
                    highest_risk = ra.risk_level

        crops_summary = ", ".join(sorted(crop_names)) if crop_names else "No plots recorded"

        result.append(
            AdminFarmerItem(
                id=f.id,
                full_name=f.full_name,
                email=f.email,
                masked_phone=mask_phone_number(f.phone_number),
                created_at=f.created_at,
                is_active=f.is_active,
                farms_count=farms_count,
                total_acreage=round(total_acres, 1),
                crops_summary=crops_summary,
                highest_risk_level=highest_risk if farms_count > 0 else None,
            )
        )

    return result


@router.get("/risks", response_model=List[AdminRiskMonitoringItem])
def list_admin_risks(
    severity: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Real-time risk surveillance across all farms from the deterministic engine."""
    stmt = (
        select(RiskAssessment)
        .join(Farm, RiskAssessment.farm_id == Farm.id)
        .options(selectinload(RiskAssessment.farm))
    )
    if severity:
        stmt = stmt.where(RiskAssessment.risk_level == severity.upper())

    stmt = stmt.order_by(desc(RiskAssessment.risk_score), desc(RiskAssessment.assessed_at)).limit(limit)
    assessments = list(db.scalars(stmt).all())

    return [
        AdminRiskMonitoringItem(
            farm_id=ra.farm_id,
            farm_name=ra.farm.farm_name if ra.farm else "Unknown Farm",
            district=ra.farm.district if ra.farm else "Unassigned District",
            highest_risk_level=ra.risk_level,
            risk_score=round(ra.risk_score, 1),
            risk_category=ra.risk_category.replace("_", " ").title(),
            assessed_at=ra.assessed_at,
        )
        for ra in assessments
    ]


@router.get("/agent-activity", response_model=List[AdminAgentActivityItem])
def list_admin_agent_activity(
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Real reasoning sessions from the Strands Agronomy Assistant."""
    stmt = (
        select(Conversation)
        .join(User, Conversation.farmer_id == User.id)
        .join(Farm, Conversation.farm_id == Farm.id)
        .options(
            selectinload(Conversation.farmer),
            selectinload(Conversation.farm),
            selectinload(Conversation.messages),
        )
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
    )
    convs = list(db.scalars(stmt).all())

    items: List[AdminAgentActivityItem] = []
    for c in convs:
        snippet = None
        if c.messages:
            last_msg = c.messages[-1]
            snippet = last_msg.content[:100]

        items.append(
            AdminAgentActivityItem(
                session_id=c.id,
                farmer_name=c.farmer.full_name if c.farmer else "Farmer",
                farm_name=c.farm.farm_name if c.farm else "Farm",
                title=c.title,
                messages_count=len(c.messages),
                last_activity_at=c.updated_at,
                last_query_snippet=snippet,
            )
        )

    return items


@router.patch("/farmers/{farmer_id}/status", response_model=FarmerActionResponse)
def update_farmer_status(
    farmer_id: uuid.UUID,
    payload: FarmerStatusUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Activate or suspend a farmer account."""
    if farmer_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot alter active status of your own administrator account.",
        )

    user = db.scalar(select(User).where(User.id == farmer_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found.",
        )
    if user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified user is an administrator and cannot be modified via farmer status endpoint.",
        )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    action_str = "activated" if user.is_active else "suspended"
    return FarmerActionResponse(
        message=f"Farmer '{user.full_name}' has been {action_str}.",
        farmer_id=user.id,
        is_active=user.is_active,
    )


@router.delete("/farmers/{farmer_id}", response_model=FarmerActionResponse)
def delete_farmer(
    farmer_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Permanently delete a farmer account and all associated parcels & records."""
    if farmer_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own administrator account.",
        )

    user = db.scalar(select(User).where(User.id == farmer_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found.",
        )
    if user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified user is an administrator and cannot be deleted via this endpoint.",
        )

    farmer_name = user.full_name
    db.delete(user)
    db.commit()

    return FarmerActionResponse(
        message=f"Farmer '{farmer_name}' and all associated farms and records have been deleted.",
        farmer_id=farmer_id,
        is_active=False,
    )


