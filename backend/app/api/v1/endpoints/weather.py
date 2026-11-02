import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_farmer
from app.models.user import User
from app.api.v1.endpoints.farms import get_farmer_farm
from app.schemas.weather import (
    WeatherObservationResponse,
    WeatherForecastResponse,
    DailyForecastResponse,
)
from app.services.weather.service import WeatherService

router = APIRouter()


@router.get(
    "/{farm_id}/weather/current",
    response_model=WeatherObservationResponse,
    summary="Get current weather for farm",
)
async def get_current_weather(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves current weather observation for the farm.
    Returns cached data if recent (15-min TTL), or fetches fresh data from Open-Meteo.
    Enforces strict farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    weather_service = WeatherService(db)
    observation = await weather_service.get_current_weather(farm, force_refresh=False)
    return observation


@router.get(
    "/{farm_id}/weather/forecast",
    response_model=WeatherForecastResponse,
    summary="Get short-term weather forecast for farm",
)
async def get_weather_forecast(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Retrieves daily multi-day forecast for the farm.
    Enforces strict farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    weather_service = WeatherService(db)
    observation = await weather_service.get_current_weather(farm, force_refresh=False)

    forecast_items: List[DailyForecastResponse] = []
    if observation.forecast_data and isinstance(observation.forecast_data, list):
        for f in observation.forecast_data:
            forecast_items.append(DailyForecastResponse(**f))

    return WeatherForecastResponse(
        farm_id=farm.id,
        provider=observation.provider,
        observed_at=observation.observed_at,
        fetched_at=observation.fetched_at,
        forecast=forecast_items,
    )


@router.post(
    "/{farm_id}/weather/refresh",
    response_model=WeatherObservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually refresh weather observation from provider",
)
async def refresh_weather(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
):
    """
    Forces a fresh fetch from Open-Meteo API.
    Subject to a 60-second cooldown rate limit to prevent provider abuse.
    Enforces strict farm ownership.
    """
    farm = get_farmer_farm(farm_id, current_user.id, db)
    weather_service = WeatherService(db)
    observation = await weather_service.get_current_weather(farm, force_refresh=True)
    return observation

