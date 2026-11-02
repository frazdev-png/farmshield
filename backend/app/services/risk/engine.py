import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.weather import WeatherObservation
from app.models.farm import FarmCrop
from app.services.risk.thresholds import (
    AGRONOMIC_DISCLAIMER,
    RAIN_CRITICAL_MM,
    RAIN_HIGH_MM,
    RAIN_MODERATE_MM,
    RAIN_LOW_MM,
    WIND_CRITICAL_KMH,
    WIND_HIGH_KMH,
    WIND_MODERATE_KMH,
    WIND_LOW_KMH,
    HEAT_CRITICAL_C,
    HEAT_HIGH_C,
    HEAT_MODERATE_C,
    HEAT_LOW_C,
    FROST_CRITICAL_C,
    FROST_HIGH_C,
    FROST_MODERATE_C,
    FROST_LOW_C,
    FUNGAL_RH_CRITICAL,
    FUNGAL_RH_HIGH,
    FUNGAL_RH_MODERATE,
    FUNGAL_TEMP_MIN_C,
    FUNGAL_TEMP_MAX_C,
)

logger = logging.getLogger("farmshield.risk.engine")


class EvaluatedRisk(BaseModel):
    risk_category: str
    risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    risk_score: float  # 0.0 to 100.0
    evidence: Dict[str, Any]
    explanation: str
    recommended_precaution: str
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeterministicRiskEngine:
    """
    Deterministic Agro-Climatic Risk Engine.
    Uses transparent, rule-based agronomic logic.
    Does NOT use machine learning or LLMs.
    Does NOT prescribe chemicals or pesticides.
    """

    CATEGORIES = [
        "Heavy Rain Risk",
        "High Wind Risk",
        "Extreme Heat Risk",
        "Low Temperature Risk",
        "High Humidity / Fungal Disease Favorable Conditions",
    ]

    def evaluate_all(
        self,
        observation: Optional[WeatherObservation],
        crops: Optional[List[FarmCrop]] = None,
    ) -> List[EvaluatedRisk]:
        """
        Evaluates all 5 risk categories for the given observation and crops.
        If observation is None or missing necessary data for a category,
        does NOT fabricate safe alerts.
        """
        if not observation:
            logger.warning("No weather observation provided for risk evaluation; skipping alert generation.")
            return []

        crop_list = crops or []
        evaluations: List[EvaluatedRisk] = []

        # 1. Heavy Rain Risk
        rain_eval = self._evaluate_heavy_rain(observation, crop_list)
        if rain_eval:
            evaluations.append(rain_eval)

        # 2. High Wind Risk
        wind_eval = self._evaluate_high_wind(observation, crop_list)
        if wind_eval:
            evaluations.append(wind_eval)

        # 3. Extreme Heat Risk
        heat_eval = self._evaluate_extreme_heat(observation, crop_list)
        if heat_eval:
            evaluations.append(heat_eval)

        # 4. Low Temperature Risk
        frost_eval = self._evaluate_low_temperature(observation, crop_list)
        if frost_eval:
            evaluations.append(frost_eval)

        # 5. High Humidity / Fungal Conditions Risk
        fungal_eval = self._evaluate_fungal_disease(observation, crop_list)
        if fungal_eval:
            evaluations.append(fungal_eval)

        return evaluations

    def _get_crop_context(self, crops: List[FarmCrop]) -> Dict[str, Any]:
        """Summarizes crop context without inventing undocumented crop thresholds."""
        crop_names = [c.crop_name for c in crops]
        return {
            "crops_count": len(crops),
            "crops_registered": crop_names,
            "disclaimer": AGRONOMIC_DISCLAIMER,
        }

    def _evaluate_heavy_rain(
        self, obs: WeatherObservation, crops: List[FarmCrop]
    ) -> Optional[EvaluatedRisk]:
        """Evaluates Heavy Rain Risk."""
        precip = obs.precipitation
        # If precipitation is missing, evidence is insufficient -> do not generate alert
        if precip is None:
            logger.info("Missing precipitation data for farm %s; skipping heavy rain evaluation.", obs.farm_id)
            return None

        # Look at forecast daily precipitation if available to capture impending deluge
        forecast_precip_max = 0.0
        if obs.forecast_data and isinstance(obs.forecast_data, list):
            for day in obs.forecast_data[:2]:  # Today and tomorrow
                d_p = day.get("precipitation_sum")
                if d_p is not None and float(d_p) > forecast_precip_max:
                    forecast_precip_max = float(d_p)

        effective_precip = max(precip, forecast_precip_max)
        crop_ctx = self._get_crop_context(crops)

        if effective_precip >= RAIN_CRITICAL_MM:
            level = "CRITICAL"
            score = min(100.0, 85.0 + 15.0 * ((effective_precip - RAIN_CRITICAL_MM) / 50.0))
            explanation = (
                f"Severe precipitation event detected ({effective_precip:.1f} mm). "
                f"High probability of soil waterlogging, root asphyxiation, topsoil erosion, and nutrient leaching."
            )
            precaution = (
                "Immediately inspect farm drainage systems, clear debris from field culverts, "
                "and suspend heavy machinery operations to prevent severe soil compaction."
            )
        elif effective_precip >= RAIN_HIGH_MM:
            level = "HIGH"
            score = 65.0 + 19.9 * ((effective_precip - RAIN_HIGH_MM) / (RAIN_CRITICAL_MM - RAIN_HIGH_MM))
            explanation = (
                f"Heavy precipitation detected ({effective_precip:.1f} mm). "
                f"Saturated soil conditions, localized pooling, and surface runoff risks are elevated."
            )
            precaution = (
                "Ensure drainage waterways are open and flowing freely. Delay planned irrigation and "
                "monitor low-lying parcels."
            )
        elif effective_precip >= RAIN_MODERATE_MM:
            level = "MODERATE"
            score = 35.0 + 29.9 * ((effective_precip - RAIN_MODERATE_MM) / (RAIN_HIGH_MM - RAIN_MODERATE_MM))
            explanation = (
                f"Moderate rainfall observed ({effective_precip:.1f} mm). "
                f"Adequate moisture accumulation with potential slow drainage in heavy clay soils."
            )
            precaution = (
                "Check moisture retention in heavy soils before running field tractors."
            )
        else:
            level = "LOW"
            score = max(0.0, 34.0 * (effective_precip / RAIN_MODERATE_MM))
            explanation = (
                f"Light or negligible precipitation observed ({effective_precip:.1f} mm). "
                f"Moisture conditions remain stable within routine agronomic ranges."
            )
            precaution = "Continue routine field monitoring and normal crop management."

        evidence = {
            "current_precipitation_mm": precip,
            "forecast_peak_precipitation_mm": forecast_precip_max,
            "effective_precipitation_mm": round(effective_precip, 2),
            "threshold_critical_mm": RAIN_CRITICAL_MM,
            "threshold_high_mm": RAIN_HIGH_MM,
            "crop_context": crop_ctx,
        }

        return EvaluatedRisk(
            risk_category="Heavy Rain Risk",
            risk_level=level,
            risk_score=round(score, 1),
            evidence=evidence,
            explanation=explanation,
            recommended_precaution=precaution,
        )

    def _evaluate_high_wind(
        self, obs: WeatherObservation, crops: List[FarmCrop]
    ) -> Optional[EvaluatedRisk]:
        """Evaluates High Wind Risk."""
        wind = obs.wind_speed
        if wind is None:
            logger.info("Missing wind speed data for farm %s; skipping high wind evaluation.", obs.farm_id)
            return None

        # Check daily forecast peak wind if present
        forecast_wind_max = 0.0
        if obs.forecast_data and isinstance(obs.forecast_data, list):
            for day in obs.forecast_data[:2]:
                d_w = day.get("wind_speed_max")
                if d_w is not None and float(d_w) > forecast_wind_max:
                    forecast_wind_max = float(d_w)

        effective_wind = max(wind, forecast_wind_max)
        crop_ctx = self._get_crop_context(crops)

        if effective_wind >= WIND_CRITICAL_KMH:
            level = "CRITICAL"
            score = min(100.0, 85.0 + 15.0 * ((effective_wind - WIND_CRITICAL_KMH) / 30.0))
            explanation = (
                f"Gale-force wind speeds ({effective_wind:.1f} km/h). "
                f"High danger of crop lodging, stalk snapping, structural polytunnel damage, and complete spray loss."
            )
            precaution = (
                "Secure all nursery coverings, shade netting, and temporary irrigation piping. "
                "Completely suspend all foliar spray operations."
            )
        elif effective_wind >= WIND_HIGH_KMH:
            level = "HIGH"
            score = 65.0 + 19.9 * ((effective_wind - WIND_HIGH_KMH) / (WIND_CRITICAL_KMH - WIND_HIGH_KMH))
            explanation = (
                f"Strong wind conditions ({effective_wind:.1f} km/h). "
                f"High risk of mechanical lodging in tall standing crops and severe spray droplet drift."
            )
            precaution = (
                "Postpone foliar applications to avoid off-target drift. Inspect windbreak hedges and "
                "verify plant stakes on vulnerable crops."
            )
        elif effective_wind >= WIND_MODERATE_KMH:
            level = "MODERATE"
            score = 35.0 + 29.9 * ((effective_wind - WIND_MODERATE_KMH) / (WIND_HIGH_KMH - WIND_MODERATE_KMH))
            explanation = (
                f"Moderate breeze ({effective_wind:.1f} km/h). Elevated risk of spray drift."
            )
            precaution = (
                "Use drift-reducing nozzle tips if applying treatments or defer until wind subsides."
            )
        else:
            level = "LOW"
            score = max(0.0, 34.0 * (effective_wind / WIND_MODERATE_KMH))
            explanation = (
                f"Gentle air movement ({effective_wind:.1f} km/h). Safe conditions for field operations."
            )
            precaution = "Optimal weather window for routine cultural activities and applications."

        evidence = {
            "current_wind_speed_kmh": wind,
            "forecast_peak_wind_kmh": forecast_wind_max,
            "effective_wind_kmh": round(effective_wind, 2),
            "threshold_critical_kmh": WIND_CRITICAL_KMH,
            "threshold_high_kmh": WIND_HIGH_KMH,
            "crop_context": crop_ctx,
        }

        return EvaluatedRisk(
            risk_category="High Wind Risk",
            risk_level=level,
            risk_score=round(score, 1),
            evidence=evidence,
            explanation=explanation,
            recommended_precaution=precaution,
        )

    def _evaluate_extreme_heat(
        self, obs: WeatherObservation, crops: List[FarmCrop]
    ) -> Optional[EvaluatedRisk]:
        """Evaluates Extreme Heat Risk."""
        temp = obs.temperature
        if temp is None:
            logger.info("Missing temperature data for farm %s; skipping extreme heat evaluation.", obs.farm_id)
            return None

        # Check forecast daily max temp if available
        forecast_temp_max = temp
        if obs.forecast_data and isinstance(obs.forecast_data, list):
            for day in obs.forecast_data[:2]:
                d_t = day.get("temperature_max")
                if d_t is not None and float(d_t) > forecast_temp_max:
                    forecast_temp_max = float(d_t)

        effective_temp = max(temp, forecast_temp_max)
        crop_ctx = self._get_crop_context(crops)

        if effective_temp >= HEAT_CRITICAL_C:
            level = "CRITICAL"
            score = min(100.0, 85.0 + 15.0 * ((effective_temp - HEAT_CRITICAL_C) / 10.0))
            explanation = (
                f"Extreme scorching heat wave ({effective_temp:.1f}°C). "
                f"Severe hazard of floral desiccation, pollen sterility, and intense crop water stress."
            )
            precaution = (
                "Execute pre-dawn or nocturnal irrigation to reduce soil canopy temperature. "
                "Provide temporary shading over sensitive nursery plants and suspend midday field work."
            )
        elif effective_temp >= HEAT_HIGH_C:
            level = "HIGH"
            score = 65.0 + 19.9 * ((effective_temp - HEAT_HIGH_C) / (HEAT_CRITICAL_C - HEAT_HIGH_C))
            explanation = (
                f"High thermal stress conditions ({effective_temp:.1f}°C). "
                f"Elevated evapotranspiration and potential stomatal closure."
            )
            precaution = (
                "Ensure soil profile moisture is adequate prior to midday heat. "
                "Avoid foliar applications during peak heat to prevent leaf scorching."
            )
        elif effective_temp >= HEAT_MODERATE_C:
            level = "MODERATE"
            score = 35.0 + 29.9 * ((effective_temp - HEAT_MODERATE_C) / (HEAT_HIGH_C - HEAT_MODERATE_C))
            explanation = (
                f"Elevated temperatures ({effective_temp:.1f}°C). "
                f"Higher plant water consumption rates."
            )
            precaution = (
                "Monitor soil moisture depletion closely and adjust irrigation volume to match crop demand."
            )
        else:
            level = "LOW"
            score = max(0.0, min(34.0, 34.0 * max(0.0, (effective_temp - 15.0) / (HEAT_MODERATE_C - 15.0))))
            explanation = (
                f"Temperature ({effective_temp:.1f}°C) is within comfortable vegetative growth ranges."
            )
            precaution = "Maintain standard irrigation schedules and routine crop management."

        evidence = {
            "current_temperature_c": temp,
            "forecast_peak_temp_c": forecast_temp_max,
            "effective_temp_c": round(effective_temp, 2),
            "threshold_critical_c": HEAT_CRITICAL_C,
            "threshold_high_c": HEAT_HIGH_C,
            "crop_context": crop_ctx,
        }

        return EvaluatedRisk(
            risk_category="Extreme Heat Risk",
            risk_level=level,
            risk_score=round(score, 1),
            evidence=evidence,
            explanation=explanation,
            recommended_precaution=precaution,
        )

    def _evaluate_low_temperature(
        self, obs: WeatherObservation, crops: List[FarmCrop]
    ) -> Optional[EvaluatedRisk]:
        """Evaluates Low Temperature / Frost Risk."""
        temp = obs.temperature
        if temp is None:
            logger.info("Missing temperature data for farm %s; skipping low temperature evaluation.", obs.farm_id)
            return None

        # Check forecast daily min temp if available
        forecast_temp_min = temp
        if obs.forecast_data and isinstance(obs.forecast_data, list):
            for day in obs.forecast_data[:2]:
                d_t = day.get("temperature_min")
                if d_t is not None and float(d_t) < forecast_temp_min:
                    forecast_temp_min = float(d_t)

        effective_temp = min(temp, forecast_temp_min)
        crop_ctx = self._get_crop_context(crops)

        if effective_temp <= FROST_CRITICAL_C:
            level = "CRITICAL"
            freeze_depth = abs(effective_temp)
            score = min(100.0, 85.0 + 15.0 * (freeze_depth / 10.0))
            explanation = (
                f"Sub-zero freezing event ({effective_temp:.1f}°C). "
                f"Severe hazard of intracellular ice crystallization and permanent vegetative tissue mortality."
            )
            precaution = (
                "Deploy emergency frost mitigation: apply light nocturnal irrigation to release latent heat, "
                "cover sensitive crops with thermal fleece, and avoid cultivating dry topsoil."
            )
        elif effective_temp <= FROST_HIGH_C:
            level = "HIGH"
            score = 65.0 + 19.9 * ((FROST_HIGH_C - effective_temp) / (FROST_HIGH_C - FROST_CRITICAL_C))
            explanation = (
                f"Near-freezing temperatures detected ({effective_temp:.1f}°C). "
                f"High risk of radiation frost under clear night skies and low wind."
            )
            precaution = (
                "Protect seedling beds and young horticulture blocks with floating row covers before dusk. "
                "Ensure soil has sufficient moisture to absorb and re-radiate ground heat."
            )
        elif effective_temp <= FROST_MODERATE_C:
            level = "MODERATE"
            score = 35.0 + 29.9 * ((FROST_MODERATE_C - effective_temp) / (FROST_MODERATE_C - FROST_HIGH_C))
            explanation = (
                f"Chilling temperatures ({effective_temp:.1f}°C). "
                f"Slowed nutrient uptake and cold stress for warm-season cultivars."
            )
            precaution = (
                "Delay sowing of warm-season seeds into cold seedbeds; monitor emergent seedlings."
            )
        else:
            level = "LOW"
            score = max(0.0, min(34.0, 34.0 * max(0.0, (FROST_LOW_C - effective_temp) / (FROST_LOW_C - FROST_MODERATE_C))))
            explanation = (
                f"Temperatures ({effective_temp:.1f}°C) remain comfortably above chilling and frost injury thresholds."
            )
            precaution = "No frost precautions required; proceed with standard seasonal operations."

        evidence = {
            "current_temperature_c": temp,
            "forecast_min_temp_c": forecast_temp_min,
            "effective_temp_c": round(effective_temp, 2),
            "threshold_critical_c": FROST_CRITICAL_C,
            "threshold_high_c": FROST_HIGH_C,
            "crop_context": crop_ctx,
        }

        return EvaluatedRisk(
            risk_category="Low Temperature Risk",
            risk_level=level,
            risk_score=round(score, 1),
            evidence=evidence,
            explanation=explanation,
            recommended_precaution=precaution,
        )

    def _evaluate_fungal_disease(
        self, obs: WeatherObservation, crops: List[FarmCrop]
    ) -> Optional[EvaluatedRisk]:
        """Evaluates High Humidity / Fungal Disease Favorable Conditions."""
        rh = obs.relative_humidity
        temp = obs.temperature

        if rh is None or temp is None:
            logger.info("Missing relative humidity or temperature for farm %s; skipping fungal evaluation.", obs.farm_id)
            return None

        crop_ctx = self._get_crop_context(crops)
        is_temp_optimal = FUNGAL_TEMP_MIN_C <= temp <= FUNGAL_TEMP_MAX_C

        if rh >= FUNGAL_RH_CRITICAL and is_temp_optimal:
            level = "CRITICAL"
            score = min(100.0, 85.0 + 15.0 * ((rh - FUNGAL_RH_CRITICAL) / 15.0))
            explanation = (
                f"Highly favorable fungal disease micro-climate: Relative humidity at {rh:.1f}% "
                f"combined with warm canopy temperature ({temp:.1f}°C) optimizes leaf wetness duration and spore germination."
            )
            precaution = (
                "Immediately conduct rigorous field scouting for foliar lesions, rust pustules, or powdery mildew. "
                "Avoid late-day overhead sprinkler irrigation and ensure adequate canopy airflow."
            )
        elif rh >= FUNGAL_RH_HIGH and (12.0 <= temp <= 32.0):
            level = "HIGH"
            score = 65.0 + 19.9 * ((rh - FUNGAL_RH_HIGH) / (FUNGAL_RH_CRITICAL - FUNGAL_RH_HIGH))
            explanation = (
                f"Elevated atmospheric humidity ({rh:.1f}%) within favorable incubation temperature range ({temp:.1f}°C). "
                f"High potential for fungal pathogen sporulation and incubation."
            )
            precaution = (
                "Scout high-density crop zones and low-lying canopy sections. "
                "Ensure row spacing promotes canopy drying."
            )
        elif rh >= FUNGAL_RH_MODERATE and (10.0 <= temp <= 35.0):
            level = "MODERATE"
            score = 35.0 + 29.9 * ((rh - FUNGAL_RH_MODERATE) / (FUNGAL_RH_HIGH - FUNGAL_RH_MODERATE))
            explanation = (
                f"Moderate humidity levels ({rh:.1f}%) and ambient temperature ({temp:.1f}°C). "
                f"Moderate baseline fungal presence potential."
            )
            precaution = (
                "Maintain routine canopy visual scouting during regular field inspections."
            )
        else:
            level = "LOW"
            score = max(0.0, min(34.0, 34.0 * (rh / FUNGAL_RH_MODERATE)))
            explanation = (
                f"Relative humidity ({rh:.1f}%) is low or ambient temperature ({temp:.1f}°C) "
                f"is outside the optimal fungal pathogen incubation envelope."
            )
            precaution = "Low risk of fungal spore germination under current environmental dryness."

        evidence = {
            "current_relative_humidity": rh,
            "current_temperature_c": temp,
            "threshold_critical_rh": FUNGAL_RH_CRITICAL,
            "threshold_high_rh": FUNGAL_RH_HIGH,
            "optimal_temperature_range": [FUNGAL_TEMP_MIN_C, FUNGAL_TEMP_MAX_C],
            "crop_context": crop_ctx,
        }

        return EvaluatedRisk(
            risk_category="High Humidity / Fungal Disease Favorable Conditions",
            risk_level=level,
            risk_score=round(score, 1),
            evidence=evidence,
            explanation=explanation,
            recommended_precaution=precaution,
        )

