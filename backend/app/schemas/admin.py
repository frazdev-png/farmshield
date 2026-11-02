import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AdminOverviewStats(BaseModel):
    total_farmers: int
    total_farms: int
    total_monitored_acres: float
    active_threats_count: int
    total_ai_queries_count: int
    total_notifications_count: int
    system_status: str = "OPERATIONAL"


class AdminFarmerItem(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    masked_phone: str
    created_at: datetime
    is_active: bool
    farms_count: int
    total_acreage: float
    crops_summary: str
    highest_risk_level: Optional[str] = None


class AdminRiskMonitoringItem(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    district: str
    highest_risk_level: str
    risk_score: float
    risk_category: str
    assessed_at: datetime


class AdminAgentActivityItem(BaseModel):
    session_id: uuid.UUID
    farmer_name: str
    farm_name: str
    title: str
    messages_count: int
    last_activity_at: datetime
    last_query_snippet: Optional[str] = None


class FarmerStatusUpdateRequest(BaseModel):
    is_active: bool


class FarmerActionResponse(BaseModel):
    message: str
    farmer_id: uuid.UUID
    is_active: Optional[bool] = None


