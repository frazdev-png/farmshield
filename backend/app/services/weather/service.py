import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.farm import Farm
from app.models.weather import WeatherObservation
from app.services.weather.base import AbstractWeatherProvider, WeatherProviderError
from app.services.weather.open_meteo import OpenMeteoProvider

logger = logging.getLogger("farmshield.weather.service")


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class WeatherService:
    CACHE_TTL_SECONDS: int = 900  # 15 minutes cache window
    REFRESH_COOLDOWN_SECONDS: int = 60  # 60 seconds minimum interval for manual refresh

    def __init__(self, db: Session, provider: Optional[AbstractWeatherProvider] = None):
        self.db = db
        self.provider = provider or OpenMeteoProvider()

    def get_latest_observation(self, farm_id) -> Optional[WeatherObservation]:
        """Queries the most recent weather observation recorded for a given farm."""
        stmt = (
            select(WeatherObservation)
            .where(WeatherObservation.farm_id == farm_id)
            .order_by(desc(WeatherObservation.fetched_at))
            .limit(1)
        )
        return self.db.scalar(stmt)

    async def get_current_weather(
        self, farm: Farm, force_refresh: bool = False
    ) -> WeatherObservation:
        """
        Retrieves weather for the farm.
        Uses cached observation if fresh. If forced, checks cooldown before fetching from provider.
        """
        latest = self.get_latest_observation(farm.id)
        now_utc = datetime.now(timezone.utc)

        # 1. Check cache validity for non-forced requests
        if latest and not force_refresh:
            fetched_at_utc = to_utc(latest.fetched_at)
            age = (now_utc - fetched_at_utc).total_seconds()
            if age < self.CACHE_TTL_SECONDS:
                logger.debug("Returning cached weather observation for farm %s (age: %.1fs)", farm.id, age)
                return latest

        # 2. Enforce refresh cooldown if requested manually
        if force_refresh and latest:
            fetched_at_utc = to_utc(latest.fetched_at)
            cooldown_remaining = self.REFRESH_COOLDOWN_SECONDS - (now_utc - fetched_at_utc).total_seconds()
            if cooldown_remaining > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: Please wait {int(cooldown_remaining)} seconds before refreshing weather data again.",
                )

        # 3. Fetch from provider
        try:
            weather_data = await self.provider.get_weather(
                latitude=farm.latitude,
                longitude=farm.longitude,
            )
        except WeatherProviderError as exc:
            logger.error("Weather provider failed for farm %s: %s", farm.id, exc)
            # If we have a cached observation, return it with a warning rather than failing completely
            if latest:
                logger.warning("Provider failed, falling back to older cached observation for farm %s", farm.id)
                return latest
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to retrieve weather data: {str(exc)}",
            ) from exc

        # 4. Check for deduplication (same farm_id, provider, and observed_at)
        existing_stmt = select(WeatherObservation).where(
            WeatherObservation.farm_id == farm.id,
            WeatherObservation.provider == weather_data.provider,
            WeatherObservation.observed_at == weather_data.observed_at,
        )
        existing = self.db.scalar(existing_stmt)
        if existing:
            # Update fetched_at and latest telemetry
            existing.fetched_at = now_utc
            existing.temperature = weather_data.temperature
            existing.relative_humidity = weather_data.relative_humidity
            existing.precipitation = weather_data.precipitation
            existing.wind_speed = weather_data.wind_speed
            existing.weather_condition = weather_data.weather_condition
            existing.forecast_data = [item.model_dump() for item in weather_data.daily_forecasts]
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # 5. Persist new observation
        new_obs = WeatherObservation(
            farm_id=farm.id,
            provider=weather_data.provider,
            observed_at=weather_data.observed_at,
            fetched_at=weather_data.fetched_at,
            temperature=weather_data.temperature,
            relative_humidity=weather_data.relative_humidity,
            precipitation=weather_data.precipitation,
            wind_speed=weather_data.wind_speed,
            weather_condition=weather_data.weather_condition,
            forecast_data=[item.model_dump() for item in weather_data.daily_forecasts],
        )
        self.db.add(new_obs)
        self.db.commit()
        self.db.refresh(new_obs)
        return new_obs

    async def get_forecast(self, farm: Farm) -> List[Dict[str, Any]]:
        """Retrieves short-term forecast for the farm."""
        obs = await self.get_current_weather(farm, force_refresh=False)
        return obs.forecast_data or []
