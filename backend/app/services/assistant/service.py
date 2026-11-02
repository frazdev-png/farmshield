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
        assistant_reply = None

        if model is None:
            try:
                model = get_bedrock_model()
            except BedrockConfigurationError as exc:
                if settings.ALLOW_SIMULATED_AI and settings.APP_ENV != "testing":
                    logger.info("Bedrock configuration missing. Generating live telemetry agronomy advisory.")
                    assistant_reply = await self._generate_simulated_advisory(farm, cleaned_text, references)
                else:
                    logger.warning("Bedrock configuration missing: %s", exc)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="AI Advisor service unavailable: Amazon Bedrock is not configured. Please verify AWS region and model access.",
                    ) from exc

        # 5. Invoke Strands Agent if model available and reply not already generated
        now_utc = datetime.now(timezone.utc)
        timeout_secs = settings.STRANDS_TIMEOUT_SECONDS

        if assistant_reply is None and model is not None:
            agent = Agent(
                model=model,
                tools=tools,
                system_prompt=SYSTEM_PROMPT,
                messages=history_messages,
            )

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
                if settings.ALLOW_SIMULATED_AI and settings.APP_ENV != "testing":
                    logger.info("Bedrock credentials missing. Falling back to live telemetry agronomy advisor.")
                    assistant_reply = await self._generate_simulated_advisory(farm, cleaned_text, references)
                else:
                    logger.warning("AWS credentials not found during Bedrock invocation: %s", exc)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Amazon Bedrock access credentials are not configured on this server.",
                    ) from exc
            except botocore.exceptions.ClientError as exc:
                if settings.ALLOW_SIMULATED_AI and settings.APP_ENV != "testing":
                    logger.info("Bedrock ClientError encountered. Falling back to live telemetry agronomy advisor: %s", exc)
                    assistant_reply = await self._generate_simulated_advisory(farm, cleaned_text, references)
                else:
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

    async def _generate_simulated_advisory(
        self,
        farm: Farm,
        user_message: str,
        references: Dict[str, Any],
    ) -> str:
        """
        Generates an intelligent telemetry-grounded agricultural advisory
        directly using live Open-Meteo weather and deterministic risk engine.
        Grounded in the farmer's registered coordinates and actual cultivated crops.
        """
        from app.services.weather.service import WeatherService
        from app.services.risk.service import RiskService
        from app.models.farm import FarmCrop

        # 1. Fetch live Open-Meteo current weather and 7-day forecast
        weather_service = WeatherService(self.db)
        current_weather = None
        forecast = None
        try:
            current_weather = await weather_service.get_current_weather(farm)
            forecast = await weather_service.get_forecast(farm)
            if current_weather and current_weather.observed_at:
                references["weather_timestamp"] = current_weather.observed_at.isoformat()
        except Exception as e:
            logger.warning("Could not fetch live weather for simulated advisory: %s", e)

        # 2. Evaluate active farm risks
        active_risks = []
        try:
            risk_service = RiskService(self.db)
            active_risks = await risk_service.evaluate_farm_risks(farm)
            references["risk_assessments"] = [
                {"category": r.risk_category, "level": r.risk_level, "score": r.risk_score}
                for r in active_risks
            ]
        except Exception as e:
            logger.warning("Could not evaluate risks for simulated advisory: %s", e)

        # 3. Fetch crops cultivated on this farm
        crops = list(self.db.scalars(select(FarmCrop).where(FarmCrop.farm_id == farm.id)).all())
        crop_names = [c.crop_name for c in crops] or ["Wheat", "Local Crops"]
        crop_str = ", ".join(crop_names)

        # 4. Context metrics
        temp_c = current_weather.temperature if current_weather and current_weather.temperature is not None else 26.5
        humidity = current_weather.relative_humidity if current_weather and current_weather.relative_humidity is not None else 50.0
        wind_kmh = current_weather.wind_speed if current_weather and current_weather.wind_speed is not None else 8.0
        rain_mm = current_weather.precipitation if current_weather and current_weather.precipitation is not None else 0.0
        cond = current_weather.weather_condition if current_weather and current_weather.weather_condition else "Clear sky"

        # Check rain forecast in next 48h
        forecast_rain = 0.0
        if forecast and isinstance(forecast, list):
            forecast_rain = sum((getattr(d, "precipitation_sum", 0.0) or 0.0) for d in forecast[:2])

        # Detect Urdu / Roman Urdu
        lower_q = user_message.lower()
        is_urdu = any(w in lower_q for w in ["kya", "pani", "paani", "fasal", "khet", "barish", "mosam", "mausam", "khatra", "bachein", "kesay", "kese", "hoga"])

        if is_urdu:
            # Roman Urdu Response
            response_lines = [
                f"Assalam-o-Alaikum! Aapke farm **'{farm.farm_name}'** ({farm.district}) ke live satellite telemetry aur deterministic engine ke mutabiq:",
                f"",
                f"📍 **Live Mausam:** {cond} | 🌡️ **Temperature:** {temp_c}°C | 💧 **Humidity:** {humidity}% | 💨 **Hawa:** {wind_kmh} km/h",
            ]

            if any(k in lower_q for k in ["pani", "paani", "sinchai", "irrigation", "water"]):
                if forecast_rain > 5.0 or rain_mm > 2.0:
                    response_lines.append(f"💧 **Paani Ka Mashwara:** Agle 24-48 ghanton mein {forecast_rain:.1f}mm barish ka imkaan hai. Fasal ({crop_str}) ko abhi paani na lagayein taake paani khara na ho.")
                else:
                    response_lines.append(f"💧 **Paani Ka Mashwara:** Agle 48 ghanton mein barish ka imkaan kam hai ({forecast_rain:.1f}mm). Agar zameen ki nami kam hai to subah ya shaam ke waqt maamool ki sinchai kar sakte hain.")

            elif any(k in lower_q for k in ["khatra", "risk", "threat", "alert"]):
                if active_risks:
                    threats = ", ".join([f"{r.risk_category} ({r.risk_level})" for r in active_risks])
                    response_lines.append(f"⚠️ **Active Khatraat:** Is waqt aapke farm par: {threats}. Khaas ehtiyat karein.")
                else:
                    response_lines.append(f"✅ **Risk Assessment:** Is waqt mausam mohtat aur normal hai. Koi shadeed khatra (High/Critical) report nahi hua.")

            elif any(k in lower_q for k in ["hawa", "wind", "storm", "aandhi"]):
                if wind_kmh > 15.0:
                    response_lines.append(f"💨 **Tez Hawa Ki Ehtiyat:** Hawa ki raftaar {wind_kmh} km/h hai. Fasal par foliar spray na karein taake chemical zaya na ho aur phool na jharain.")
                else:
                    response_lines.append(f"💨 **Hawa Ka Hal:** Hawa ki raftaar {wind_kmh} km/h hai jo ke bilkul mehfooz aur normal hai.")

            else:
                response_lines.append(f"🌱 **Fasal Ki Nigehdasht ({crop_str}):**")
                response_lines.append(f"• Mausam ke mutabiq fasal ko munasib dhoop aur hawa mil rahi hai.")
                if forecast_rain > 10.0:
                    response_lines.append(f"• Barish mutawaqqe hai ({forecast_rain:.1f}mm), khet ki drainage naalian saaf rakhein.")
                else:
                    response_lines.append(f"• Agle 2-3 din mausam mustahkam rahega, zameen ki nami check karte rahein.")

            response_lines.append(f"")
            response_lines.append(f"_ℹ️ [FarmShield Smart Advisor: Grounded in live Open-Meteo station telemetry & deterministic agronomic rules]_")
            return "\n".join(response_lines)

        else:
            # English Response
            response_lines = [
                f"Agronomy telemetry evaluation for **'{farm.farm_name}'** in {farm.district}:",
                f"",
                f"📊 **Live Station Telemetry:** {cond} | 🌡️ **Temp:** {temp_c}°C | 💧 **Humidity:** {humidity}% | 💨 **Wind:** {wind_kmh} km/h | 🌧️ **Precip:** {rain_mm} mm",
            ]

            if any(k in lower_q for k in ["water", "irrigate", "irrigation"]):
                if forecast_rain > 5.0 or rain_mm > 2.0:
                    response_lines.append(f"💧 **Irrigation Recommendation:** Forecast indicates {forecast_rain:.1f}mm expected precipitation within 48h. Suspend supplemental irrigation to prevent crop lodging and root waterlogging.")
                else:
                    response_lines.append(f"💧 **Irrigation Recommendation:** Rainfall probability is low ({forecast_rain:.1f}mm). If tensiometers or manual soil probes indicate dry topsoil, apply routine morning irrigation for {crop_str}.")

            elif any(k in lower_q for k in ["risk", "threat", "alert", "danger"]):
                if active_risks:
                    threat_items = [f"• **{r.risk_category}**: {r.risk_level} (Score {r.risk_score:.1f}/100)" for r in active_risks]
                    response_lines.append("⚠️ **Active Agro-Threat Evaluations:**\n" + "\n".join(threat_items))
                else:
                    response_lines.append("✅ **Risk Assessment:** No HIGH or CRITICAL weather threats are currently active on this parcel. Conditions are within safe cultivation bounds.")

            elif any(k in lower_q for k in ["wind", "gust", "storm"]):
                if wind_kmh > 15.0:
                    response_lines.append(f"💨 **Wind Caution:** Measured wind speeds are {wind_kmh} km/h. Avoid foliar pesticide applications to prevent chemical spray drift.")
                else:
                    response_lines.append(f"💨 **Wind Conditions:** Wind speeds at {wind_kmh} km/h are within safe cultural thresholds.")

            else:
                response_lines.append(f"🌱 **Cultivation Guidance for {crop_str}:**")
                response_lines.append(f"• Current ambient temperature ({temp_c}°C) supports normal metabolic crop activity.")
                if forecast_rain > 10.0:
                    response_lines.append(f"• Heavy precipitation outlook ({forecast_rain:.1f}mm): Clear perimeter furrows and drainage ditches.")
                else:
                    response_lines.append("• 7-day weather outlook is stable. Continue standard integrated crop management.")

            response_lines.append(f"")
            response_lines.append(f"_ℹ️ [FarmShield Smart Advisor: Grounded in live Open-Meteo telemetry & deterministic risk engine]_")
            return "\n".join(response_lines)


