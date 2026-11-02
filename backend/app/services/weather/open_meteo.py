import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx

from app.services.weather.base import (
    AbstractWeatherProvider,
    WeatherData,
    DailyForecastItem,
    WeatherProviderError,
)

logger = logging.getLogger("farmshield.weather.open_meteo")

WMO_CODE_MAP: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def interpret_wmo_code(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODE_MAP.get(code, f"Weather Code {code}")


class OpenMeteoProvider(AbstractWeatherProvider):
    """
    Open-Meteo weather provider implementation.
    Free, non-commercial/academic tier requiring no API key.
    """

    BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    CONNECT_TIMEOUT_SECONDS: float = 5.0
    READ_TIMEOUT_SECONDS: float = 10.0

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def get_weather(self, latitude: float, longitude: float) -> WeatherData:
        """
        Retrieves weather telemetry from Open-Meteo API using farm coordinates.
        Never fabricates live weather values.
        """
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "UTC",
        }

        timeout = httpx.Timeout(
            connect=self.CONNECT_TIMEOUT_SECONDS,
            read=self.READ_TIMEOUT_SECONDS,
            write=5.0,
            pool=5.0,
        )

        try:
            if self._client:
                response = await self._client.get(self.BASE_URL, params=params, timeout=timeout)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(self.BASE_URL, params=params)

            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException as exc:
            logger.warning("Open-Meteo API timeout for coords (%s, %s): %s", latitude, longitude, exc)
            raise WeatherProviderError("Weather provider request timed out. Please try again.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            logger.error("Open-Meteo HTTP error %d: %s", status_code, exc)
            raise WeatherProviderError(f"Weather provider error: HTTP {status_code}.") from exc
        except httpx.RequestError as exc:
            logger.error("Open-Meteo request error for coords (%s, %s): %s", latitude, longitude, exc)
            raise WeatherProviderError("Weather provider connection failed.") from exc
        except Exception as exc:
            logger.error("Open-Meteo response decoding failed: %s", exc)
            raise WeatherProviderError("Invalid weather response from provider.") from exc

        return self._parse_response(data, latitude, longitude)

    def _parse_response(self, data: Dict[str, Any], latitude: float, longitude: float) -> WeatherData:
        """Safely parses JSON payload from Open-Meteo."""
        if not isinstance(data, dict):
            raise WeatherProviderError("Invalid payload format received from weather provider.")

        current = data.get("current")
        if not current or not isinstance(current, dict):
            raise WeatherProviderError("Missing 'current' telemetry in weather provider response.")

        # Parse observed timestamp (UTC)
        time_str = current.get("time")
        if time_str:
            try:
                # Open-Meteo UTC timestamps are formatted e.g. "2026-11-01T06:45"
                if not time_str.endswith("Z") and "+" not in time_str:
                    time_str += "+00:00"
                observed_at = datetime.fromisoformat(time_str)
            except Exception:
                observed_at = datetime.now(timezone.utc)
        else:
            observed_at = datetime.now(timezone.utc)

        weather_code = current.get("weather_code")
        condition = interpret_wmo_code(weather_code)

        # Parse daily forecast
        daily_forecasts: List[DailyForecastItem] = []
        daily_data = data.get("daily", {})
        if isinstance(daily_data, dict) and "time" in daily_data:
            dates = daily_data.get("time", [])
            w_codes = daily_data.get("weather_code", [])
            max_temps = daily_data.get("temperature_2m_max", [])
            min_temps = daily_data.get("temperature_2m_min", [])
            precips = daily_data.get("precipitation_sum", [])
            winds = daily_data.get("wind_speed_10m_max", [])

            for i in range(len(dates)):
                d_date = str(dates[i])
                d_code = w_codes[i] if i < len(w_codes) else None
                d_cond = interpret_wmo_code(d_code)
                d_max_t = float(max_temps[i]) if i < len(max_temps) and max_temps[i] is not None else None
                d_min_t = float(min_temps[i]) if i < len(min_temps) and min_temps[i] is not None else None
                d_precip = float(precips[i]) if i < len(precips) and precips[i] is not None else None
                d_wind = float(winds[i]) if i < len(winds) and winds[i] is not None else None

                daily_forecasts.append(
                    DailyForecastItem(
                        date=d_date,
                        weather_code=d_code,
                        weather_condition=d_cond,
                        temperature_max=d_max_t,
                        temperature_min=d_min_t,
                        precipitation_sum=d_precip,
                        wind_speed_max=d_wind,
                    )
                )

        # Current metrics (may be None if station unavailable)
        temp = float(current["temperature_2m"]) if current.get("temperature_2m") is not None else None
        humidity = float(current["relative_humidity_2m"]) if current.get("relative_humidity_2m") is not None else None
        precipitation = float(current["precipitation"]) if current.get("precipitation") is not None else None
        wind_speed = float(current["wind_speed_10m"]) if current.get("wind_speed_10m") is not None else None

        return WeatherData(
            provider="open-meteo",
            latitude=latitude,
            longitude=longitude,
            observed_at=observed_at,
            fetched_at=datetime.now(timezone.utc),
            temperature=temp,
            relative_humidity=humidity,
            precipitation=precipitation,
            wind_speed=wind_speed,
            weather_code=weather_code,
            weather_condition=condition,
            daily_forecasts=daily_forecasts,
        )

