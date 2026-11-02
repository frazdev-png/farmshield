import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_farmer
from app.models.user import User
from app.api.v1.endpoints.farms import get_farmer_farm
from app.schemas.risk import (
    RiskAssessmentResponse,
    RiskSummaryResponse,
)
from app.services.risk.service import RiskService

router = APIRouter()

SEVERITY_ORDER = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MODERATE": 2,
    "LOW": 1,
}


def build_risk_summary(farm_id: uuid.UUID, assessments: List) -> RiskSummaryResponse:
    if not assessments:
        return RiskSummaryResponse(
            farm_id=farm_id,
            overall_risk_level="LOW",
            highest_risk_score=0.0,
            assessed_at=datetime.now(timezone.utc),
            assessments=[],
        )

    # Determine highest severity level and score
    highest_score = max(a.risk_score for a in assessments)
    highest_level = max(assessments, key=lambda a: SEVERITY_ORDER.get(a.risk_level, 0)).risk_level
    latest_assessed_at = max(a.assessed_at for a in assessments)

    return RiskSummaryResponse(
        farm_id=farm_id,
        overall_risk_level=highest_level,
        highest_risk_score=highest_score,
        assessed_at=latest_assessed_at,
        assessments=[RiskAssessmentResponse.model_validate(a) for a in assessments],
    )


@router.get(
    "/{farm_id}/risks",
    response_model=List[RiskAssessmentResponse],
    summary="Get historical risk assessments for farm",
)
def get_farm_risks(
    farm_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves historical risk assessments for the authenticated farmer's farm.
    Enforces farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    risk_service = RiskService(db)
    assessments = risk_service.get_historical_risks(farm.id, limit=limit, category=category)
    return [RiskAssessmentResponse.model_validate(a) for a in assessments]


@router.get(
    "/{farm_id}/risks/latest",
    response_model=RiskSummaryResponse,
    summary="Get latest evaluated risks and overall risk level",
)
async def get_latest_risks(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves the most recent assessment for each of the 5 agro-climatic risk categories.
    Calculates overall farm risk level and highest score.
    Automatically triggers initial evaluation if no prior assessments exist.
    Enforces farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    risk_service = RiskService(db)
    assessments = await risk_service.get_latest_risks(farm)
    return build_risk_summary(farm.id, assessments)


@router.post(
    "/{farm_id}/risks/evaluate",
    response_model=RiskSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger deterministic risk engine evaluation",
)
async def evaluate_risks(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Triggers deterministic Python risk evaluation against the farm's latest weather observation.
    Deduplicates assessments and stores results in the database.
    Returns the comprehensive summary and category breakdown.
    Enforces farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    risk_service = RiskService(db)
    assessments = await risk_service.evaluate_farm_risks(farm)
    return build_risk_summary(farm.id, assessments)

