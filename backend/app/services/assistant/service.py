import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import botocore.exceptions
from strands import Agent
from strands.types.content import Message

from app.models.farm import Farm
from app.models.conversation import Conversation, ConversationMessage
from app.core.config import settings
from app.services.assistant.model import (
    get_bedrock_model,
    BedrockConfigurationError,
    BedrockInvocationError,
)
from app.services.assistant.tools import build_farm_agent_tools
from app.services.assistant.prompts import SYSTEM_PROMPT

logger = logging.getLogger("farmshield.assistant.service")


class AssistantService:
    MAX_HISTORY_TURNS = 10  # Maximum turns of conversation history retained for context

    def __init__(self, db: Session, model_override: Optional[Any] = None):
        self.db = db
        self.model_override = model_override

    def get_or_create_conversation(
        self,
        farmer_id: uuid.UUID,
        farm: Farm,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        """
        Retrieves an existing conversation enforcing farmer & farm ownership,
        or creates a new conversation for this authorized farm.
        """
        if conversation_id:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            conv = self.db.scalar(stmt)
            if not conv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found.",
                )
            if conv.farmer_id != farmer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this conversation.",
                )
            if conv.farm_id != farm.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Conversation belongs to a different farm context.",
                )
            return conv

        # Create new conversation
        conv = Conversation(
            farmer_id=farmer_id,
            farm_id=farm.id,
            title=f"Advisory - {farm.farm_name}",
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    async def chat(
        self,
        farmer_id: uuid.UUID,
        farm: Farm,
        message_text: str,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Processes a farmer's message using the Strands AI Agent.
        Binds read-only tools to the authorized farm context.
        Records references, timestamps, and persists conversation messages.
        """
        cleaned_text = message_text.strip()
        if not cleaned_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content cannot be empty.",
            )

        if len(cleaned_text) > 2000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message exceeds maximum allowed length of 2000 characters.",
            )

        # 1. Authorize and load conversation
        conversation = self.get_or_create_conversation(farmer_id, farm, conversation_id)

        # 2. Load recent bounded conversation history (chronological order)
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(self.MAX_HISTORY_TURNS * 2)
        )
        past_msgs = list(reversed(list(self.db.scalars(stmt).all())))

        # Format Strands history messages
        history_messages: List[Message] = []
        for pm in past_msgs:
            role = "user" if pm.sender == "user" else "assistant"
            history_messages.append({"role": role, "content": [{"text": pm.content}]})

        # 3. Setup references tracker and tools
        references: Dict[str, Any] = {
            "weather_timestamp": None,
            "risk_assessments": [],
        }
        tools = build_farm_agent_tools(farm, self.db, references)

        # 4. Resolve Model
        model = self.model_override
        if model is None:
            try:
                model = get_bedrock_model()
            except BedrockConfigurationError as exc:
                logger.warning("Bedrock configuration missing: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI Advisor service unavailable: Amazon Bedrock is not configured. Please verify AWS region and model access.",
                ) from exc

        # 5. Initialize Strands Agent
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            messages=history_messages,
        )

        # 6. Invoke Strands Agent with timeout protection
        now_utc = datetime.now(timezone.utc)
        timeout_secs = settings.STRANDS_TIMEOUT_SECONDS

        try:
            result = await asyncio.wait_for(
                agent.invoke_async(cleaned_text),
                timeout=timeout_secs,
            )
            assistant_reply = str(result).strip()
            if not assistant_reply:
                assistant_reply = "I evaluated your farm conditions, but could not produce a detailed text response. Please try asking again."
        except asyncio.TimeoutError as exc:
            logger.error("Bedrock model invocation timed out after %ds", timeout_secs)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"AI Advisor request timed out after {timeout_secs} seconds. Please try again.",
            ) from exc
        except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError) as exc:
            logger.warning("AWS credentials not found during Bedrock invocation: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Amazon Bedrock access credentials are not configured on this server.",
            ) from exc
        except botocore.exceptions.ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            msg = exc.response.get("Error", {}).get("Message", str(exc))
            logger.error("Bedrock ClientError [%s]: %s", code, msg)
            if code == "AccessDeniedException":
                detail = "Amazon Bedrock access denied. Verify that the model access is enabled in the AWS account."
            elif code == "ThrottlingException":
                detail = "Amazon Bedrock request rate limit exceeded. Please wait a moment and try again."
            else:
                detail = f"AI service error from Amazon Bedrock ({code})."
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during agent execution: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI advisory response.",
            ) from exc

        # 7. Persist user and assistant messages
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            sender="user",
            content=cleaned_text,
            created_at=now_utc,
        )
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            sender="assistant",
            content=assistant_reply,
            metadata_json=references,
            created_at=datetime.now(timezone.utc),
        )
        conversation.updated_at = datetime.now(timezone.utc)

        self.db.add(user_msg)
        self.db.add(assistant_msg)
        self.db.commit()

        return {
            "conversation_id": conversation.id,
            "assistant_message": assistant_reply,
            "referenced_weather_timestamp": references["weather_timestamp"],
            "referenced_risk_assessments": references["risk_assessments"],
            "response_timestamp": assistant_msg.created_at,
        }

    def list_conversations(
        self,
        farmer_id: uuid.UUID,
        farm_id: Optional[uuid.UUID] = None,
    ) -> List[Conversation]:
        """Lists conversations belonging to authenticated farmer."""
        stmt = (
            select(Conversation)
            .where(Conversation.farmer_id == farmer_id)
        )
        if farm_id:
            stmt = stmt.where(Conversation.farm_id == farm_id)
        stmt = stmt.order_by(desc(Conversation.updated_at))
        return list(self.db.scalars(stmt).all())

    def get_conversation_messages(
        self,
        farmer_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        """Retrieves conversation with all its historical messages, verifying ownership."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = self.db.scalar(stmt)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        if conv.farmer_id != farmer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this conversation.",
            )
        return conv

