import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from strands import tool

from app.models.farm import Farm, FarmCrop
from app.models.weather import WeatherObservation
from app.models.risk import RiskAssessment
from app.services.weather.service import WeatherService
from app.services.risk.service import RiskService

logger = logging.getLogger("farmshield.assistant.tools")


def build_farm_agent_tools(
    farm: Farm,
    db: Session,
    references: Dict[str, Any],
) -> List[Any]:
    """
    Factory creating read-only Strands tools strictly bound to the authorized farm context.
    The LLM cannot alter the farm ID or access any other farmer's data.
    """

    @tool
    def get_farm_information() -> Dict[str, Any]:
        """
        Retrieves detailed information about the farmer's currently selected farm,
        including geographic coordinates, district, village, total acreage, and soil characteristics.
        """
        return {
            "farm_name": farm.farm_name,
            "district": farm.district,
            "village": farm.village,
            "address": farm.address,
            "latitude": farm.latitude,
            "longitude": farm.longitude,
            "total_area": farm.total_area,
            "area_unit": farm.area_unit,
            "soil_type": farm.soil_type or "Unspecified",
        }

    @tool
    def get_registered_crops() -> List[Dict[str, Any]]:
        """
        Retrieves the complete list of crops registered and actively cultivated on this farm,
        including crop variety, cultivated area, and sowing dates.
        """
        stmt = select(FarmCrop).where(FarmCrop.farm_id == farm.id)
        crops = list(db.scalars(stmt).all())
        if not crops:
            return [{"message": "No crops currently registered on this farm."}]

        return [
            {
                "crop_name": c.crop_name,
                "variety": c.variety or "Standard",
                "cultivated_area": c.cultivated_area,
                "area_unit": c.area_unit,
                "sowing_date": c.sowing_date.isoformat() if c.sowing_date else "Unspecified",
            }
            for c in crops
        ]

    @tool
    async def get_current_weather() -> Dict[str, Any]:
        """
        Retrieves the latest available real-time weather observation for the farm from Open-Meteo,
        including temperature, relative humidity, precipitation rate, and wind speed.
        """
        weather_service = WeatherService(db)
        try:
            obs = await weather_service.get_current_weather(farm, force_refresh=False)
            if obs:
                obs_time = obs.observed_at.isoformat() if obs.observed_at else None
                references["weather_timestamp"] = obs_time
                return {
                    "temperature_celsius": obs.temperature,
                    "relative_humidity_percent": obs.relative_humidity,
                    "precipitation_mm": obs.precipitation,
                    "wind_speed_kmh": obs.wind_speed,
                    "weather_condition": obs.weather_condition,
                    "observed_at": obs_time,
                    "provider": obs.provider,
                }
        except Exception as e:
            logger.warning("Error fetching current weather for assistant tool: %s", e)

        return {"status": "unavailable", "message": "Real-time weather station observation is currently unavailable."}

    @tool
    async def get_weather_forecast() -> List[Dict[str, Any]]:
        """
        Retrieves the multi-day weather forecast for this farm,
        including daily maximum and minimum temperatures, precipitation sums, and wind speed peaks.
        """
        weather_service = WeatherService(db)
        try:
            forecast_data = await weather_service.get_forecast(farm)
            if forecast_data:
                return forecast_data[:7]
        except Exception as e:
            logger.warning("Error fetching forecast for assistant tool: %s", e)

        return [{"status": "unavailable", "message": "Weather forecast is currently unavailable."}]

    @tool
    async def get_latest_risk_assessments() -> List[Dict[str, Any]]:
        """
        Retrieves the latest deterministic risk assessments evaluated for this farm.
        Covers Heavy Rain, High Wind, Extreme Heat, Low Temperature, and Fungal Disease risks.
        Returns risk levels, deterministic scores (0-100), explanations, and cultural precautions.
        """
        risk_service = RiskService(db)
        try:
            assessments = await risk_service.get_latest_risks(farm)
            if not assessments:
                return [{"message": "No risk assessments currently available for this farm."}]

            results = []
            for a in assessments:
                item = {
                    "risk_category": a.risk_category,
                    "risk_level": a.risk_level,
                    "risk_score": a.risk_score,
                    "explanation": a.explanation,
                    "recommended_precaution": a.recommended_precaution,
                    "assessed_at": a.assessed_at.isoformat() if a.assessed_at else None,
                }
                results.append(item)
                if a.risk_category not in references["risk_assessments"]:
                    references["risk_assessments"].append({
                        "category": a.risk_category,
                        "level": a.risk_level,
                        "score": a.risk_score,
                    })
            return results
        except Exception as e:
            logger.warning("Error fetching risk assessments for assistant tool: %s", e)

        return [{"status": "unavailable", "message": "Risk assessments are currently unavailable."}]

    @tool
    def get_risk_history(limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves a limited history of past deterministic risk evaluations for this farm (max 10).
        """
        safe_limit = max(1, min(10, limit))
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.farm_id == farm.id)
            .order_by(desc(RiskAssessment.assessed_at))
            .limit(safe_limit)
        )
        records = list(db.scalars(stmt).all())
        if not records:
            return [{"message": "No historical risk records found."}]

        return [
            {
                "risk_category": r.risk_category,
                "risk_level": r.risk_level,
                "risk_score": r.risk_score,
                "assessed_at": r.assessed_at.isoformat() if r.assessed_at else None,
            }
            for r in records
        ]

    return [
        get_farm_information,
        get_registered_crops,
        get_current_weather,
        get_weather_forecast,
        get_latest_risk_assessments,
        get_risk_history,
    ]

