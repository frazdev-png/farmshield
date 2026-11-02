from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WeatherProviderError(Exception):
    """Raised when external weather provider encounters an error, timeout, or invalid response."""
    pass


class DailyForecastItem(BaseModel):
    date: str
    weather_code: Optional[int] = None
    weather_condition: str
    temperature_max: Optional[float] = None
    temperature_min: Optional[float] = None
    precipitation_sum: Optional[float] = None
    wind_speed_max: Optional[float] = None


class WeatherData(BaseModel):
    provider: str = "open-meteo"
    latitude: float
    longitude: float
    observed_at: datetime
    fetched_at: datetime
    temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    weather_code: Optional[int] = None
    weather_condition: str = "Unknown"
    daily_forecasts: List[DailyForecastItem] = Field(default_factory=list)


class AbstractWeatherProvider(ABC):
    @abstractmethod
    async def get_weather(self, latitude: float, longitude: float) -> WeatherData:
        """Fetch current weather and short-term forecast for given coordinates."""
        pass

