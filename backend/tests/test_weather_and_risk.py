import random
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.farm import Farm, FarmCrop
from app.models.weather import WeatherObservation
from app.models.risk import RiskAssessment
from app.services.weather.base import (
    WeatherData,
    DailyForecastItem,
    WeatherProviderError,
)
from app.services.weather.open_meteo import OpenMeteoProvider, interpret_wmo_code
from app.services.weather.service import WeatherService
from app.services.risk.thresholds import (
    RAIN_CRITICAL_MM,
    RAIN_HIGH_MM,
    RAIN_MODERATE_MM,
    WIND_CRITICAL_KMH,
    WIND_HIGH_KMH,
    WIND_MODERATE_KMH,
    HEAT_CRITICAL_C,
    HEAT_HIGH_C,
    HEAT_MODERATE_C,
    FROST_CRITICAL_C,
    FROST_HIGH_C,
    FROST_MODERATE_C,
    FUNGAL_RH_CRITICAL,
    FUNGAL_RH_HIGH,
    FUNGAL_RH_MODERATE,
)
from app.services.risk.engine import DeterministicRiskEngine, EvaluatedRisk
from app.services.risk.service import RiskService


def create_authenticated_farmer(client: TestClient, name_prefix: str = "WeatherFarmer"):
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


def create_test_farm(client: TestClient, headers: dict, name: str = "Iowa Agro Farm") -> dict:
    """Helper to create a farm for testing."""
    payload = {
        "farm_name": name,
        "district": "Polk County",
        "village": "Des Moines",
        "latitude": 41.5868,
        "longitude": -93.6250,
        "total_area": 100.0,
        "area_unit": "acres",
        "soil_type": "Loam",
    }
    res = client.post("/api/v1/farms", json=payload, headers=headers)
    assert res.status_code == 201
    return res.json()


MOCK_OPEN_METEO_JSON = {
    "latitude": 41.59,
    "longitude": -93.63,
    "current": {
        "time": "2026-11-01T10:00",
        "temperature_2m": 22.5,
        "relative_humidity_2m": 60.0,
        "precipitation": 0.0,
        "weather_code": 1,
        "wind_speed_10m": 14.2,
    },
    "daily": {
        "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
        "weather_code": [1, 2, 61],
        "temperature_2m_max": [24.0, 21.0, 18.0],
        "temperature_2m_min": [12.0, 10.0, 8.0],
        "precipitation_sum": [0.0, 2.5, 12.0],
        "wind_speed_10m_max": [15.0, 20.0, 30.0],
    },
}


# ============================================================================
# 1. Weather Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_weather_provider_success():
    """Verify OpenMeteoProvider parses valid external response correctly."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_JSON
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_resp

    provider = OpenMeteoProvider(client=mock_client)
    result = await provider.get_weather(41.5868, -93.6250)

    assert result.provider == "open-meteo"
    assert result.temperature == 22.5
    assert result.relative_humidity == 60.0
    assert result.precipitation == 0.0
    assert result.wind_speed == 14.2
    assert result.weather_condition == "Mainly clear"
    assert len(result.daily_forecasts) == 3
    assert result.daily_forecasts[0].temperature_max == 24.0


@pytest.mark.asyncio
async def test_weather_provider_timeout():
    """Verify OpenMeteoProvider translates timeout into WeatherProviderError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Read timed out")

    provider = OpenMeteoProvider(client=mock_client)
    with pytest.raises(WeatherProviderError) as exc_info:
        await provider.get_weather(41.5868, -93.6250)
    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_weather_provider_unavailable_500():
    """Verify OpenMeteoProvider translates 5xx HTTP error into WeatherProviderError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    req = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    resp = httpx.Response(503, request=req)
    mock_client.get.side_effect = httpx.HTTPStatusError("Service Unavailable", request=req, response=resp)

    provider = OpenMeteoProvider(client=mock_client)
    with pytest.raises(WeatherProviderError) as exc_info:
        await provider.get_weather(41.5868, -93.6250)
    assert "503" in str(exc_info.value)


@pytest.mark.asyncio
async def test_weather_provider_invalid_response():
    """Verify OpenMeteoProvider safely handles corrupted or missing JSON fields."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": True, "reason": "Corrupt"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_resp

    provider = OpenMeteoProvider(client=mock_client)
    with pytest.raises(WeatherProviderError) as exc_info:
        await provider.get_weather(41.5868, -93.6250)
    assert "missing 'current'" in str(exc_info.value).lower()


# ============================================================================
# 2. Weather Caching & Service Tests
# ============================================================================

@pytest.mark.asyncio
async def test_weather_caching_and_cooldown(test_db: Session):
    """Verify WeatherService caches fresh observations and enforces cooldown."""
    farmer_id = uuid.uuid4()
    farm = Farm(
        farmer_id=farmer_id,
        farm_name="Cache Test Farm",
        district="Polk",
        village="Des Moines",
        latitude=41.58,
        longitude=-93.62,
        total_area=50.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    mock_provider = AsyncMock()
    mock_provider.get_weather.return_value = WeatherData(
        provider="open-meteo",
        latitude=41.58,
        longitude=-93.62,
        observed_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        temperature=20.0,
        relative_humidity=50.0,
        precipitation=0.0,
        wind_speed=10.0,
        weather_condition="Clear sky",
        daily_forecasts=[],
    )

    service = WeatherService(test_db, provider=mock_provider)

    # First fetch - should call provider
    obs1 = await service.get_current_weather(farm, force_refresh=False)
    assert obs1.temperature == 20.0
    assert mock_provider.get_weather.call_count == 1

    # Second fetch within 15 mins - should use cache without calling provider
    obs2 = await service.get_current_weather(farm, force_refresh=False)
    assert obs2.id == obs1.id
    assert mock_provider.get_weather.call_count == 1

    # Force refresh immediately - should trigger cooldown 429
    with pytest.raises(Exception) as exc:
        await service.get_current_weather(farm, force_refresh=True)
    assert exc.value.status_code == 429


# ============================================================================
# 3. Deterministic Risk Engine & Threshold Boundaries Tests
# ============================================================================

def test_risk_evaluation_heavy_rain_categories():
    """Verify Heavy Rain Risk evaluation across critical, high, moderate, low thresholds."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # 1. Critical Rain (>= 50 mm)
    obs_critical = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=55.0,
        wind_speed=10.0,
        temperature=22.0,
        relative_humidity=60.0,
    )
    res = engine._evaluate_heavy_rain(obs_critical, [])
    assert res.risk_level == "CRITICAL"
    assert 85.0 <= res.risk_score <= 100.0

    # 2. High Rain (>= 25 mm)
    obs_high = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=30.0,
        wind_speed=10.0,
        temperature=22.0,
        relative_humidity=60.0,
    )
    res = engine._evaluate_heavy_rain(obs_high, [])
    assert res.risk_level == "HIGH"
    assert 65.0 <= res.risk_score < 85.0

    # 3. Moderate Rain (>= 10 mm)
    obs_mod = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=15.0,
        wind_speed=10.0,
        temperature=22.0,
        relative_humidity=60.0,
    )
    res = engine._evaluate_heavy_rain(obs_mod, [])
    assert res.risk_level == "MODERATE"
    assert 35.0 <= res.risk_score < 65.0

    # 4. Low Rain (< 10 mm)
    obs_low = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=2.0,
        wind_speed=10.0,
        temperature=22.0,
        relative_humidity=60.0,
    )
    res = engine._evaluate_heavy_rain(obs_low, [])
    assert res.risk_level == "LOW"
    assert 0.0 <= res.risk_score < 35.0


def test_risk_evaluation_high_wind_categories():
    """Verify High Wind Risk evaluation boundaries."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # Critical wind (>= 60 km/h)
    obs_crit = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=65.0,
        temperature=20.0,
        relative_humidity=50.0,
    )
    res = engine._evaluate_high_wind(obs_crit, [])
    assert res.risk_level == "CRITICAL"
    assert 85.0 <= res.risk_score <= 100.0

    # Low wind (< 25 km/h)
    obs_low = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=10.0,
        temperature=20.0,
        relative_humidity=50.0,
    )
    res = engine._evaluate_high_wind(obs_low, [])
    assert res.risk_level == "LOW"
    assert 0.0 <= res.risk_score < 35.0


def test_risk_evaluation_extreme_heat_categories():
    """Verify Extreme Heat Risk evaluation boundaries."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # Critical heat (>= 40°C)
    obs_crit = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=5.0,
        temperature=42.0,
        relative_humidity=30.0,
    )
    res = engine._evaluate_extreme_heat(obs_crit, [])
    assert res.risk_level == "CRITICAL"
    assert 85.0 <= res.risk_score <= 100.0

    # Low heat (< 30°C)
    obs_low = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=5.0,
        temperature=24.0,
        relative_humidity=50.0,
    )
    res = engine._evaluate_extreme_heat(obs_low, [])
    assert res.risk_level == "LOW"
    assert 0.0 <= res.risk_score < 35.0


def test_risk_evaluation_low_temperature_categories():
    """Verify Low Temperature / Frost Risk evaluation boundaries."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # Subzero freeze (<= 0°C)
    obs_crit = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=2.0,
        temperature=-2.0,
        relative_humidity=80.0,
    )
    res = engine._evaluate_low_temperature(obs_crit, [])
    assert res.risk_level == "CRITICAL"
    assert 85.0 <= res.risk_score <= 100.0

    # Radiation frost hazard (<= 4°C)
    obs_high = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=2.0,
        temperature=2.0,
        relative_humidity=80.0,
    )
    res = engine._evaluate_low_temperature(obs_high, [])
    assert res.risk_level == "HIGH"
    assert 65.0 <= res.risk_score < 85.0


def test_risk_evaluation_fungal_disease_categories():
    """Verify High Humidity / Fungal Disease conditions."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # High humidity (88%) and warm temperature (24°C) -> CRITICAL
    obs_crit = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=2.0,
        wind_speed=5.0,
        temperature=24.0,
        relative_humidity=88.0,
    )
    res = engine._evaluate_fungal_disease(obs_crit, [])
    assert res.risk_level == "CRITICAL"
    assert 85.0 <= res.risk_score <= 100.0

    # Low humidity (40%) -> LOW
    obs_low = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=0.0,
        wind_speed=5.0,
        temperature=22.0,
        relative_humidity=40.0,
    )
    res = engine._evaluate_fungal_disease(obs_low, [])
    assert res.risk_level == "LOW"
    assert 0.0 <= res.risk_score < 35.0


def test_missing_weather_data_handling():
    """Verify missing weather telemetry does not generate false alerts."""
    engine = DeterministicRiskEngine()
    dummy_farm_id = uuid.uuid4()

    # Weather observation with None fields
    obs_missing = WeatherObservation(
        farm_id=dummy_farm_id,
        observed_at=datetime.now(timezone.utc),
        precipitation=None,
        wind_speed=None,
        temperature=None,
        relative_humidity=None,
    )
    # When fields are None, evaluate_all returns empty list (does NOT claim LOW / safe)
    results = engine.evaluate_all(obs_missing, [])
    assert len(results) == 0


def test_duplicate_assessment_prevention(test_db: Session):
    """Verify duplicate assessments for the same observation and category are not duplicated."""
    farmer_id = uuid.uuid4()
    farm = Farm(
        farmer_id=farmer_id,
        farm_name="Deduplication Farm",
        district="Polk",
        village="Des Moines",
        latitude=41.58,
        longitude=-93.62,
        total_area=20.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()

    obs = WeatherObservation(
        farm_id=farm.id,
        observed_at=datetime.now(timezone.utc),
        temperature=22.0,
        relative_humidity=60.0,
        precipitation=1.0,
        wind_speed=12.0,
    )
    test_db.add(obs)
    test_db.commit()

    mock_weather_service = MagicMock()
    mock_weather_service.get_current_weather = AsyncMock(return_value=obs)

    risk_service = RiskService(test_db, weather_service=mock_weather_service)

    # First evaluation
    pytest_asyncio_result1 = None
    import asyncio
    assessments1 = asyncio.run(risk_service.evaluate_farm_risks(farm))
    assert len(assessments1) == 5

    count1 = test_db.query(RiskAssessment).filter(RiskAssessment.farm_id == farm.id).count()
    assert count1 == 5

    # Second evaluation on the same observation - should update existing, NOT add 5 new records
    assessments2 = asyncio.run(risk_service.evaluate_farm_risks(farm))
    assert len(assessments2) == 5

    count2 = test_db.query(RiskAssessment).filter(RiskAssessment.farm_id == farm.id).count()
    assert count2 == 5  # No duplicates created


# ============================================================================
# 4. API Endpoints & Ownership/Authorization Integration Tests
# ============================================================================

def test_unauthenticated_weather_and_risk_rejected(client: TestClient):
    """Verify unauthenticated requests to weather and risk endpoints are rejected (401)."""
    fake_id = uuid.uuid4()
    assert client.get(f"/api/v1/farms/{fake_id}/weather/current").status_code == 401
    assert client.get(f"/api/v1/farms/{fake_id}/weather/forecast").status_code == 401
    assert client.post(f"/api/v1/farms/{fake_id}/weather/refresh").status_code == 401
    assert client.get(f"/api/v1/farms/{fake_id}/risks").status_code == 401
    assert client.get(f"/api/v1/farms/{fake_id}/risks/latest").status_code == 401
    assert client.post(f"/api/v1/farms/{fake_id}/risks/evaluate").status_code == 401


@patch("app.services.weather.open_meteo.OpenMeteoProvider.get_weather")
def test_cross_farmer_weather_access_rejected(mock_get_weather, client: TestClient):
    """Verify Farmer B cannot view or refresh weather for Farmer A's farm (403)."""
    mock_get_weather.return_value = WeatherData(
        provider="open-meteo",
        latitude=41.58,
        longitude=-93.62,
        observed_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        temperature=22.0,
        relative_humidity=55.0,
        precipitation=0.0,
        wind_speed=12.0,
        weather_condition="Clear sky",
        daily_forecasts=[],
    )

    _, headers_farmer_a = create_authenticated_farmer(client, "WeatherFarmerA")
    _, headers_farmer_b = create_authenticated_farmer(client, "WeatherFarmerB")

    farm_a = create_test_farm(client, headers_farmer_a, "Farmer A's Cornfield")
    farm_a_id = farm_a["id"]

    # Farmer B attempts to get Farmer A's current weather
    res1 = client.get(f"/api/v1/farms/{farm_a_id}/weather/current", headers=headers_farmer_b)
    assert res1.status_code == 403

    # Farmer B attempts to refresh Farmer A's weather
    res2 = client.post(f"/api/v1/farms/{farm_a_id}/weather/refresh", headers=headers_farmer_b)
    assert res2.status_code == 403


@patch("app.services.weather.open_meteo.OpenMeteoProvider.get_weather")
def test_cross_farmer_risk_access_rejected(mock_get_weather, client: TestClient):
    """Verify Farmer B cannot view or evaluate risks on Farmer A's farm (403)."""
    mock_get_weather.return_value = WeatherData(
        provider="open-meteo",
        latitude=41.58,
        longitude=-93.62,
        observed_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        temperature=22.0,
        relative_humidity=55.0,
        precipitation=0.0,
        wind_speed=12.0,
        weather_condition="Clear sky",
        daily_forecasts=[],
    )

    _, headers_farmer_a = create_authenticated_farmer(client, "RiskFarmerA")
    _, headers_farmer_b = create_authenticated_farmer(client, "RiskFarmerB")

    farm_a = create_test_farm(client, headers_farmer_a, "Farmer A's Wheatfield")
    farm_a_id = farm_a["id"]

    # Farmer B attempts to view risks
    res1 = client.get(f"/api/v1/farms/{farm_a_id}/risks/latest", headers=headers_farmer_b)
    assert res1.status_code == 403

    # Farmer B attempts to evaluate risks
    res2 = client.post(f"/api/v1/farms/{farm_a_id}/risks/evaluate", headers=headers_farmer_b)
    assert res2.status_code == 403


@patch("app.services.weather.open_meteo.OpenMeteoProvider.get_weather")
def test_weather_and_risk_end_to_end_flow(mock_get_weather, client: TestClient):
    """Verify complete end-to-end weather retrieval, forecast, and risk evaluation flow."""
    mock_get_weather.return_value = WeatherData(
        provider="open-meteo",
        latitude=41.5868,
        longitude=-93.6250,
        observed_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        temperature=28.5,
        relative_humidity=82.0,
        precipitation=32.0,
        wind_speed=45.0,
        weather_condition="Heavy rain",
        daily_forecasts=[
            DailyForecastItem(
                date="2026-11-01",
                weather_code=65,
                weather_condition="Heavy rain",
                temperature_max=29.0,
                temperature_min=18.0,
                precipitation_sum=35.0,
                wind_speed_max=48.0,
            ),
            DailyForecastItem(
                date="2026-11-02",
                weather_code=3,
                weather_condition="Overcast",
                temperature_max=24.0,
                temperature_min=15.0,
                precipitation_sum=5.0,
                wind_speed_max=25.0,
            ),
        ],
    )

    _, headers = create_authenticated_farmer(client, "FlowFarmer")
    farm = create_test_farm(client, headers, "End-to-End Agri Farm")
    farm_id = farm["id"]

    # 1. Get current weather
    res_weather = client.get(f"/api/v1/farms/{farm_id}/weather/current", headers=headers)
    assert res_weather.status_code == 200
    weather_data = res_weather.json()
    assert weather_data["temperature"] == 28.5
    assert weather_data["precipitation"] == 32.0
    assert weather_data["provider"] == "open-meteo"

    # 2. Get forecast
    res_forecast = client.get(f"/api/v1/farms/{farm_id}/weather/forecast", headers=headers)
    assert res_forecast.status_code == 200
    forecast_data = res_forecast.json()
    assert len(forecast_data["forecast"]) == 2
    assert forecast_data["forecast"][0]["weather_condition"] == "Heavy rain"

    # 3. Evaluate risks
    res_eval = client.post(f"/api/v1/farms/{farm_id}/risks/evaluate", headers=headers)
    assert res_eval.status_code == 200
    risk_summary = res_eval.json()
    assert risk_summary["overall_risk_level"] in ["HIGH", "CRITICAL"]
    assert len(risk_summary["assessments"]) == 5

    # Check that Heavy Rain was evaluated as HIGH or CRITICAL because precip is 32.0mm (> 25mm)
    heavy_rain = next(a for a in risk_summary["assessments"] if a["risk_category"] == "Heavy Rain Risk")
    assert heavy_rain["risk_level"] in ["HIGH", "CRITICAL"]
    assert heavy_rain["risk_score"] >= 65.0
    assert "precaution" in heavy_rain["recommended_precaution"].lower() or len(heavy_rain["recommended_precaution"]) > 10

    # 4. Get latest risks
    res_latest = client.get(f"/api/v1/farms/{farm_id}/risks/latest", headers=headers)
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["overall_risk_level"] == risk_summary["overall_risk_level"]

    # 5. Get historical risks
    res_hist = client.get(f"/api/v1/farms/{farm_id}/risks?limit=10", headers=headers)
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 5

