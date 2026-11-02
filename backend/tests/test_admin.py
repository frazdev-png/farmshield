import random
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.models.risk import RiskAssessment
from app.models.conversation import Conversation, ConversationMessage
from app.core.security import create_access_token


def create_user(db: Session, role: str = "farmer") -> User:
    unique_suffix = random.randint(1000000, 9999999)
    user = User(
        full_name=f"Test {role.title()} {unique_suffix}",
        email=f"{role}_{unique_suffix}@example.com",
        phone_number=f"+1555{unique_suffix}",
        password_hash="mock_hash",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role, email=user.email)


def test_admin_endpoints_require_authentication(client: TestClient):
    endpoints = [
        "/api/v1/admin/overview",
        "/api/v1/admin/farmers",
        "/api/v1/admin/risks",
        "/api/v1/admin/agent-activity",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 401, f"Expected 401 for unauthenticated {ep}"


def test_admin_endpoints_reject_farmer(client: TestClient, test_db: Session):
    farmer = create_user(test_db, role="farmer")
    token = get_token(farmer)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/v1/admin/overview",
        "/api/v1/admin/farmers",
        "/api/v1/admin/risks",
        "/api/v1/admin/agent-activity",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 403, f"Expected 403 for farmer accessing {ep}"


def test_admin_overview_metrics(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer1 = create_user(test_db, role="farmer")
    farmer2 = create_user(test_db, role="farmer")

    # Create farms
    farm1 = Farm(
        farmer_id=farmer1.id,
        farm_name="North Agro Field",
        district="Faisalabad",
        village="Chak 204",
        latitude=31.4187,
        longitude=73.0791,
        total_area=25.0,
        area_unit="acres",
    )
    farm2 = Farm(
        farmer_id=farmer2.id,
        farm_name="Southern Orchard",
        district="Multan",
        village="Basti Malook",
        latitude=30.1575,
        longitude=71.5249,
        total_area=15.5,
        area_unit="acres",
    )
    test_db.add_all([farm1, farm2])
    test_db.commit()

    # Create risk
    risk = RiskAssessment(
        farm_id=farm1.id,
        risk_category="HEAVY_RAIN",
        risk_level="HIGH",
        risk_score=80.0,
        evidence={"rainfall_mm": 60.0},
        explanation="Forecast indicates >50mm rain.",
        recommended_precaution="Clear drainage ditches.",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)

    # Create assistant conversation and messages
    conv = Conversation(farmer_id=farmer1.id, farm_id=farm1.id)
    test_db.add(conv)
    test_db.commit()

    msg = ConversationMessage(
        conversation_id=conv.id,
        sender="user",
        content="What should I do about the storm?",
    )
    test_db.add(msg)
    test_db.commit()

    token = get_token(admin)
    res = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert "total_farmers" in data
    assert "total_farms" in data
    assert "total_monitored_acres" in data
    assert "active_threats_count" in data
    assert "total_ai_queries_count" in data

    assert data["total_farmers"] >= 2
    assert data["total_farms"] >= 2
    assert data["total_monitored_acres"] >= 40.5
    assert data["active_threats_count"] >= 1
    assert data["total_ai_queries_count"] >= 1


def test_admin_farmers_directory(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer = create_user(test_db, role="farmer")

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Green Pastures",
        district="Sahiwal",
        village="Village 9",
        latitude=30.6682,
        longitude=73.1114,
        total_area=18.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    crop = FarmCrop(
        farm_id=farm.id,
        crop_name="Basmati Rice",
        variety="Super Kernal",
        cultivated_area=10.0,
        area_unit="acres",
    )
    test_db.add(crop)
    test_db.commit()

    token = get_token(admin)
    res = client.get("/api/v1/admin/farmers", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    farmers_list = res.json()
    assert isinstance(farmers_list, list)

    target = next((f for f in farmers_list if f["id"] == str(farmer.id)), None)
    assert target is not None
    assert target["full_name"] == farmer.full_name
    assert target["email"] == farmer.email
    # Phone number should be masked for privacy in admin overview
    assert "****" in target["masked_phone"]
    assert target["farms_count"] >= 1
    assert target["total_acreage"] >= 18.0
    assert "Basmati Rice" in target["crops_summary"]


def test_admin_risks_list(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer = create_user(test_db, role="farmer")

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Delta Estate",
        district="Larkana",
        village="Waqas",
        latitude=27.5589,
        longitude=68.2020,
        total_area=30.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="EXTREME_HEAT",
        risk_level="HIGH",
        risk_score=85.0,
        evidence={"max_temp": 45.0},
        explanation="Temperatures exceeding 43C.",
        recommended_precaution="Irrigate during evening.",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)
    test_db.commit()

    token = get_token(admin)
    res = client.get("/api/v1/admin/risks", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    risks_list = res.json()
    assert isinstance(risks_list, list)

    target_risk = next((r for r in risks_list if r["farm_name"] == "Delta Estate"), None)
    assert target_risk is not None
    assert target_risk["risk_category"] == "Extreme Heat"
    assert target_risk["highest_risk_level"] == "HIGH"
    assert target_risk["district"] == "Larkana"


def test_admin_agent_activity_list(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer = create_user(test_db, role="farmer")

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Sunrise Valley",
        district="Okara",
        village="Chak 45",
        latitude=30.8080,
        longitude=73.4458,
        total_area=12.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    conv = Conversation(farmer_id=farmer.id, farm_id=farm.id)
    test_db.add(conv)
    test_db.commit()

    msg = ConversationMessage(
        conversation_id=conv.id,
        sender="user",
        content="When should I apply urea fertilizer to my wheat crop?",
    )
    test_db.add(msg)
    test_db.commit()

    token = get_token(admin)
    res = client.get("/api/v1/admin/agent-activity", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    activities = res.json()
    assert isinstance(activities, list)

    target_activity = next((a for a in activities if a["session_id"] == str(conv.id)), None)
    assert target_activity is not None
    assert target_activity["farmer_name"] == farmer.full_name
    assert target_activity["farm_name"] == "Sunrise Valley"
    assert "fertilizer" in target_activity["last_query_snippet"]


def test_weather_coordinates_passed_to_open_meteo_provider(client: TestClient, test_db: Session):
    from unittest.mock import patch, AsyncMock
    from app.services.weather.base import WeatherData

    farmer = create_user(test_db, role="farmer")
    token = get_token(farmer)
    headers = {"Authorization": f"Bearer {token}"}

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Isolated Coordinate Farm",
        district="Vehari",
        village="Tibba",
        latitude=30.0452,
        longitude=72.3489,
        total_area=10.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    now = datetime.now(timezone.utc)
    mock_weather = WeatherData(
        latitude=30.0452,
        longitude=72.3489,
        temperature=28.5,
        relative_humidity=45.0,
        precipitation=0.0,
        wind_speed=12.0,
        weather_condition="Clear sky",
        observed_at=now,
        fetched_at=now,
        daily_forecasts=[],
    )

    with patch("app.services.weather.open_meteo.OpenMeteoProvider.get_weather", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_weather
        res = client.get(f"/api/v1/farms/{farm.id}/weather/current", headers=headers)
        assert res.status_code == 200
        mock_get.assert_called_once_with(latitude=30.0452, longitude=72.3489)


def test_weather_provider_failure_returns_error_response(client: TestClient, test_db: Session):
    from unittest.mock import patch, AsyncMock
    from app.services.weather.base import WeatherProviderError

    farmer = create_user(test_db, role="farmer")
    token = get_token(farmer)
    headers = {"Authorization": f"Bearer {token}"}

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Faulty Weather Farm",
        district="Kasur",
        village="Raja Jang",
        latitude=31.1167,
        longitude=74.4500,
        total_area=5.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    with patch("app.services.weather.open_meteo.OpenMeteoProvider.get_weather", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = WeatherProviderError("Open-Meteo gateway timeout")
        res = client.get(f"/api/v1/farms/{farm.id}/weather/current", headers=headers)
        assert res.status_code in [502, 503]


def test_admin_can_toggle_farmer_status(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer = create_user(test_db, role="farmer")
    admin_headers = {"Authorization": f"Bearer {get_token(admin)}"}

    # Suspend farmer
    res = client.patch(
        f"/api/v1/admin/farmers/{farmer.id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # Reactivate farmer
    res = client.patch(
        f"/api/v1/admin/farmers/{farmer.id}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is True


def test_admin_can_delete_farmer_and_cascades(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    farmer = create_user(test_db, role="farmer")
    admin_headers = {"Authorization": f"Bearer {get_token(admin)}"}

    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Cascade Farm",
        district="Sahiwal",
        village="Chak 45",
        latitude=30.6682,
        longitude=73.1114,
        total_area=25.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    res = client.delete(f"/api/v1/admin/farmers/{farmer.id}", headers=admin_headers)
    assert res.status_code == 200
    assert "deleted" in res.json()["message"].lower()

    # Verify farmer and farm are removed
    assert test_db.query(User).filter(User.id == farmer.id).first() is None
    assert test_db.query(Farm).filter(Farm.id == farm.id).first() is None


def test_admin_cannot_delete_self(client: TestClient, test_db: Session):
    admin = create_user(test_db, role="admin")
    admin_headers = {"Authorization": f"Bearer {get_token(admin)}"}

    res = client.delete(f"/api/v1/admin/farmers/{admin.id}", headers=admin_headers)
    assert res.status_code == 400


def test_farmer_cannot_delete_farmer(client: TestClient, test_db: Session):
    farmer_a = create_user(test_db, role="farmer")
    farmer_b = create_user(test_db, role="farmer")
    headers = {"Authorization": f"Bearer {get_token(farmer_a)}"}

    res = client.delete(f"/api/v1/admin/farmers/{farmer_b.id}", headers=headers)
    assert res.status_code == 403


