import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ChatRequest(BaseModel):
    farm_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=2000, description="Farmer advisory query")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Optional existing conversation thread ID")


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    assistant_message: str
    referenced_weather_timestamp: Optional[str] = None
    referenced_risk_assessments: Optional[List[Dict[str, Any]]] = None
    response_timestamp: datetime


class ConversationMessageResponse(BaseModel):
    id: uuid.UUID
    sender: str  # user or assistant
    content: str
    metadata_json: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse]

    model_config = ConfigDict(from_attributes=True)


class ConversationSummaryResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages_count: int

    model_config = ConfigDict(from_attributes=True)

