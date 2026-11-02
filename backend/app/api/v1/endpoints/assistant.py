import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_farmer
from app.models.user import User
from app.api.v1.endpoints.farms import get_farmer_farm
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    ConversationMessageResponse,
)
from app.services.assistant.service import AssistantService

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with FarmShield Strands AI Agronomy Advisor",
)
async def chat_with_assistant(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Executes a turn with the FarmShield AI Agronomy Advisor.
    Enforces strict farm ownership: tools are bound exclusively to the authenticated farmer's selected farm.
    Stores and persists conversation history.
    """
    farm = get_farmer_farm(payload.farm_id, current_user.id, db)
    assistant_service = AssistantService(db)
    result = await assistant_service.chat(
        farmer_id=current_user.id,
        farm=farm,
        message_text=payload.message,
        conversation_id=payload.conversation_id,
    )
    return ChatResponse(**result)


@router.get(
    "/conversations",
    response_model=List[ConversationSummaryResponse],
    summary="List farmer advisory conversation threads",
)
def list_conversations(
    farm_id: Optional[uuid.UUID] = Query(None, description="Filter threads by farm ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves all conversation threads owned by the authenticated farmer, optionally filtered by farm.
    """
    if farm_id:
        get_farmer_farm(farm_id, current_user.id, db)

    assistant_service = AssistantService(db)
    conversations = assistant_service.list_conversations(
        farmer_id=current_user.id,
        farm_id=farm_id,
    )

    return [
        ConversationSummaryResponse(
            id=c.id,
            farmer_id=c.farmer_id,
            farm_id=c.farm_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            messages_count=len(c.messages) if c.messages else 0,
        )
        for c in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation history thread",
)
def get_conversation_history(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves all messages in a conversation thread.
    Enforces strict conversation ownership.
    """
    assistant_service = AssistantService(db)
    conv = assistant_service.get_conversation_messages(
        farmer_id=current_user.id,
        conversation_id=conversation_id,
    )

    return ConversationDetailResponse(
        id=conv.id,
        farmer_id=conv.farmer_id,
        farm_id=conv.farm_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[ConversationMessageResponse.model_validate(m) for m in conv.messages],
    )

