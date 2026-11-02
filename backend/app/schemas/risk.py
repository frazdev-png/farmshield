import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class RiskAssessmentResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    weather_observation_id: Optional[uuid.UUID] = None
    risk_category: str
    risk_level: str
    risk_score: float
    evidence: Dict[str, Any]
    explanation: str
    recommended_precaution: str
    assessed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskSummaryResponse(BaseModel):
    farm_id: uuid.UUID
    overall_risk_level: str
    highest_risk_score: float
    assessed_at: datetime
    assessments: List[RiskAssessmentResponse]

