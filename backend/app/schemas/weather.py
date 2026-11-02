import uuid
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict


class DailyForecastResponse(BaseModel):
    date: str
    weather_code: Optional[int] = None
    weather_condition: str
    temperature_max: Optional[float] = None
    temperature_min: Optional[float] = None
    precipitation_sum: Optional[float] = None
    wind_speed_max: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class WeatherObservationResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    provider: str
    observed_at: datetime
    fetched_at: datetime
    temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    weather_condition: Optional[str] = None
    forecast_data: Optional[List[DailyForecastResponse]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherForecastResponse(BaseModel):
    farm_id: uuid.UUID
    provider: str
    observed_at: datetime
    fetched_at: datetime
    forecast: List[DailyForecastResponse]

