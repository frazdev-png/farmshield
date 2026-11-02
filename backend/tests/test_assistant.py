import random
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import botocore.exceptions
from strands.agent.agent_result import AgentResult

from app.models.farm import Farm, FarmCrop
from app.models.weather import WeatherObservation
from app.models.risk import RiskAssessment
from app.models.conversation import Conversation, ConversationMessage
from app.services.assistant.tools import build_farm_agent_tools
from app.services.assistant.service import AssistantService
from app.services.assistant.model import get_bedrock_model


def create_authenticated_farmer(client: TestClient, name_prefix: str = "AIFarmer"):
    """Helper to register and login a farmer, returning (user_data, auth_headers)."""
    unique_suffix = uuid.uuid4().hex[:8]
    phone_digits = random.randint(1000000, 9999999)
    email = f"{name_prefix.lower()}_{unique_suffix}@shieldfarm.org"
    password = "SecurePassword123!"

    reg_payload = {
        "full_name": f"{name_prefix} {unique_suffix}",
        "email": email,
        "phone_number": f"+1555{phone_digits}",
        "password": password,
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return login_res.json()["user"], headers


def create_test_farm(client: TestClient, headers: dict, name: str = "AI Test Farm") -> dict:
    """Helper to create a farm for testing."""
    payload = {
        "farm_name": name,
        "district": "Story County",
        "village": "Ames",
        "latitude": 42.0308,
        "longitude": -93.6319,
        "total_area": 120.0,
        "area_unit": "acres",
        "soil_type": "Silt Loam",
    }
    res = client.post("/api/v1/farms", json=payload, headers=headers)
    assert res.status_code == 201
    return res.json()


def make_mock_agent_result(text: str) -> AgentResult:
    """Creates a mock AgentResult with message text."""
    res = MagicMock(spec=AgentResult)
    res.interrupts = []
    res.structured_output = None
    res.message = {"role": "assistant", "content": [{"text": text}]}
    res.__str__.return_value = text
    return res


# ============================================================================
# 1. Model & Tools Unit Tests
# ============================================================================

def test_model_initialization_caching():
    """Verify get_bedrock_model returns cached instance without re-instantiating."""
    m1 = get_bedrock_model()
    m2 = get_bedrock_model()
    assert m1 is m2


@pytest.mark.asyncio
async def test_tools_execution_with_authorized_farm_context(test_db: Session):
    """Verify tools execute within pre-authorized farm boundary and read data correctly."""
    farmer_id = uuid.uuid4()
    farm = Farm(
        farmer_id=farmer_id,
        farm_name="Isolated Crop Farm",
        district="Polk",
        village="Ankeny",
        latitude=41.72,
        longitude=-93.60,
        total_area=80.0,
        area_unit="acres",
        soil_type="Clay Loam",
    )
    test_db.add(farm)
    test_db.commit()

    crop = FarmCrop(
        farm_id=farm.id,
        crop_name="Sweet Corn",
        variety="Golden Bantam",
        cultivated_area=35.0,
        area_unit="acres",
    )
    test_db.add(crop)

    obs = WeatherObservation(
        farm_id=farm.id,
        observed_at=datetime.now(timezone.utc),
        temperature=25.0,
        relative_humidity=65.0,
        precipitation=0.0,
        wind_speed=12.0,
        weather_condition="Mainly clear",
    )
    test_db.add(obs)

    risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="Heavy Rain Risk",
        risk_level="LOW",
        risk_score=15.0,
        evidence={"observed": 0.0},
        explanation="Light rain conditions",
        recommended_precaution="Routine monitoring",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)
    test_db.commit()

    references = {"weather_timestamp": None, "risk_assessments": []}
    tools = build_farm_agent_tools(farm, test_db, references)
    tool_map = {t.__name__: t for t in tools}

    # 1. Farm info
    farm_info = tool_map["get_farm_information"]()
    assert farm_info["farm_name"] == "Isolated Crop Farm"
    assert farm_info["total_area"] == 80.0

    # 2. Registered crops
    crops_info = tool_map["get_registered_crops"]()
    assert len(crops_info) == 1
    assert crops_info[0]["crop_name"] == "Sweet Corn"

    # 3. Current weather
    weather_info = await tool_map["get_current_weather"]()
    assert weather_info["temperature_celsius"] == 25.0
    assert references["weather_timestamp"] is not None

    # 4. Risk assessments
    risks_info = await tool_map["get_latest_risk_assessments"]()
    assert len(risks_info) >= 1
    assert risks_info[0]["risk_category"] == "Heavy Rain Risk"
    assert len(references["risk_assessments"]) >= 1

    # 5. Risk history
    history = tool_map["get_risk_history"](limit=5)
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_tools_missing_data_safe_handling(test_db: Session):
    """Verify tools handle missing weather and risk assessments gracefully without crashing."""
    farm = Farm(
        farmer_id=uuid.uuid4(),
        farm_name="Empty Telemetry Farm",
        district="Polk",
        village="Des Moines",
        latitude=41.58,
        longitude=-93.62,
        total_area=10.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    references = {"weather_timestamp": None, "risk_assessments": []}
    tools = build_farm_agent_tools(farm, test_db, references)
    tool_map = {t.__name__: t for t in tools}

    # Empty crops
    crops_res = tool_map["get_registered_crops"]()
    assert "No crops" in crops_res[0]["message"]

    # History empty
    hist_res = tool_map["get_risk_history"](limit=5)
    assert "No historical" in hist_res[0]["message"]


# ============================================================================
# 2. API Endpoints, Ownership & Security Tests
# ============================================================================

def test_unauthenticated_chat_rejected(client: TestClient):
    """Verify unauthenticated requests to chat endpoints are rejected (401)."""
    fake_id = uuid.uuid4()
    payload = {"farm_id": str(fake_id), "message": "Help me with frost."}
    assert client.post("/api/v1/assistant/chat", json=payload).status_code == 401
    assert client.get("/api/v1/assistant/conversations").status_code == 401
    assert client.get(f"/api/v1/assistant/conversations/{fake_id}").status_code == 401


def test_chat_message_validation(client: TestClient):
    """Verify empty messages or messages exceeding 2000 chars are rejected."""
    _, headers = create_authenticated_farmer(client, "ValidFarmer")
    farm = create_test_farm(client, headers, "Validation Farm")

    # Empty message
    res_empty = client.post("/api/v1/assistant/chat", json={"farm_id": farm["id"], "message": "   "}, headers=headers)
    assert res_empty.status_code == 422

    # Excessively long message (> 2000 chars)
    long_msg = "A" * 2005
    res_long = client.post("/api/v1/assistant/chat", json={"farm_id": farm["id"], "message": long_msg}, headers=headers)
    assert res_long.status_code == 422


@patch("strands.Agent.invoke_async")
def test_successful_mocked_assistant_chat(mock_invoke, client: TestClient):
    """Verify end-to-end assistant turn with mocked model response and references."""
    expected_reply = "Your 120-acre farm in Ames is in good condition. No severe rain is expected today."
    mock_invoke.return_value = make_mock_agent_result(expected_reply)

    _, headers = create_authenticated_farmer(client, "ChatFarmer")
    farm = create_test_farm(client, headers, "Corn & Soy Farm")

    payload = {
        "farm_id": farm["id"],
        "message": "What is the status of my farm today?",
    }
    response = client.post("/api/v1/assistant/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert expected_reply in data["assistant_message"]

    # Verify conversation history was created and can be listed
    conv_id = data["conversation_id"]
    conv_res = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers)
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert len(conv_data["messages"]) == 2  # user message + assistant reply
    assert conv_data["messages"][0]["sender"] == "user"
    assert conv_data["messages"][1]["sender"] == "assistant"


def test_cross_farmer_farm_chat_rejected(client: TestClient):
    """Verify Farmer B cannot invoke the assistant on Farmer A's farm (403)."""
    _, headers_a = create_authenticated_farmer(client, "FarmerOwnerA")
    _, headers_b = create_authenticated_farmer(client, "FarmerIntruderB")

    farm_a = create_test_farm(client, headers_a, "Farmer A Farm")

    # Farmer B attempts to chat using Farmer A's farm ID
    res = client.post(
        "/api/v1/assistant/chat",
        json={"farm_id": farm_a["id"], "message": "Give me intel on this farm."},
        headers=headers_b,
    )
    assert res.status_code == 403
    assert "access denied" in res.json()["error"]["message"].lower() or "not own" in res.json()["error"]["message"].lower()


@patch("strands.Agent.invoke_async")
def test_cross_farmer_conversation_history_isolation(mock_invoke, client: TestClient):
    """Verify Farmer B cannot access Farmer A's conversation history thread (403)."""
    mock_invoke.return_value = make_mock_agent_result("Here is your private agronomy advice.")

    _, headers_a = create_authenticated_farmer(client, "PrivateFarmerA")
    _, headers_b = create_authenticated_farmer(client, "PrivateFarmerB")

    farm_a = create_test_farm(client, headers_a, "Private Farm A")

    chat_res = client.post(
        "/api/v1/assistant/chat",
        json={"farm_id": farm_a["id"], "message": "Private crop rotation plan"},
        headers=headers_a,
    )
    assert chat_res.status_code == 200
    conv_id = chat_res.json()["conversation_id"]

    # Farmer B attempts to read Farmer A's conversation thread
    spy_res = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_b)
    assert spy_res.status_code == 403


@patch("strands.Agent.invoke_async")
def test_bedrock_missing_credentials_handling(mock_invoke, client: TestClient):
    """Verify missing AWS credentials return clean 503 error without crashing."""
    mock_invoke.side_effect = botocore.exceptions.NoCredentialsError()

    _, headers = create_authenticated_farmer(client, "NoCredsFarmer")
    farm = create_test_farm(client, headers, "NoCreds Farm")

    res = client.post(
        "/api/v1/assistant/chat",
        json={"farm_id": farm["id"], "message": "Check my soil moisture."},
        headers=headers,
    )
    assert res.status_code == 503
    assert "credentials" in res.json()["error"]["message"].lower() or "unavailable" in res.json()["error"]["message"].lower()


@patch("strands.Agent.invoke_async")
def test_bedrock_throttling_client_error_handling(mock_invoke, client: TestClient):
    """Verify Bedrock throttling exception returns clean 502 Bad Gateway."""
    error_response = {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}
    mock_invoke.side_effect = botocore.exceptions.ClientError(error_response, "InvokeModel")

    _, headers = create_authenticated_farmer(client, "ThrottledFarmer")
    farm = create_test_farm(client, headers, "Throttled Farm")

    res = client.post(
        "/api/v1/assistant/chat",
        json={"farm_id": farm["id"], "message": "Quick check."},
        headers=headers,
    )
    assert res.status_code == 502
    assert "rate limit" in res.json()["error"]["message"].lower() or "throttling" in res.json()["error"]["message"].lower()

