import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.farm import Farm
from app.models.weather import WeatherObservation
from app.models.risk import RiskAssessment
from app.services.risk.engine import DeterministicRiskEngine, EvaluatedRisk
from app.services.weather.service import WeatherService

logger = logging.getLogger("farmshield.risk.service")


class RiskService:
    def __init__(self, db: Session, weather_service: Optional[WeatherService] = None):
        self.db = db
        self.weather_service = weather_service or WeatherService(db)
        self.engine = DeterministicRiskEngine()

    async def evaluate_farm_risks(self, farm: Farm) -> List[RiskAssessment]:
        """
        Runs deterministic risk evaluation on the farm's latest weather observation and crops.
        Deduplicates against existing assessments for the same observation and category.
        """
        # Ensure we have a recent weather observation
        observation = await self.weather_service.get_current_weather(farm, force_refresh=False)
        crops = farm.crops or []

        evaluated_risks = self.engine.evaluate_all(observation, crops)
        saved_assessments: List[RiskAssessment] = []

        now_utc = datetime.now(timezone.utc)

        for item in evaluated_risks:
            # Check if an assessment already exists for this farm, weather_obs, and category
            existing_stmt = select(RiskAssessment).where(
                RiskAssessment.farm_id == farm.id,
                RiskAssessment.weather_observation_id == observation.id,
                RiskAssessment.risk_category == item.risk_category,
            )
            existing = self.db.scalar(existing_stmt)

            if existing:
                # Update existing record with updated evaluation
                existing.risk_level = item.risk_level
                existing.risk_score = item.risk_score
                existing.evidence = item.evidence
                existing.explanation = item.explanation
                existing.recommended_precaution = item.recommended_precaution
                existing.assessed_at = now_utc
                saved_assessments.append(existing)
            else:
                new_assessment = RiskAssessment(
                    farm_id=farm.id,
                    weather_observation_id=observation.id,
                    risk_category=item.risk_category,
                    risk_level=item.risk_level,
                    risk_score=item.risk_score,
                    evidence=item.evidence,
                    explanation=item.explanation,
                    recommended_precaution=item.recommended_precaution,
                    assessed_at=now_utc,
                )
                self.db.add(new_assessment)
                saved_assessments.append(new_assessment)

        self.db.commit()
        for a in saved_assessments:
            self.db.refresh(a)

        # Trigger urgent notifications for HIGH and CRITICAL risks (with built-in deduplication)
        try:
            from app.services.notification import NotificationService
            notification_service = NotificationService(self.db)
            notification_service.create_risk_notifications(farm, saved_assessments)
        except Exception as exc:
            logger.error(f"Error creating risk notifications for farm {farm.id}: {exc}")

        return saved_assessments

    async def get_latest_risks(self, farm: Farm) -> List[RiskAssessment]:
        """
        Retrieves the latest assessment for each of the 5 categories for the farm.
        If no assessments exist, automatically triggers an initial evaluation.
        """
        results: List[RiskAssessment] = []
        for cat in DeterministicRiskEngine.CATEGORIES:
            stmt = (
                select(RiskAssessment)
                .where(
                    RiskAssessment.farm_id == farm.id,
                    RiskAssessment.risk_category == cat,
                )
                .order_by(desc(RiskAssessment.assessed_at))
                .limit(1)
            )
            latest = self.db.scalar(stmt)
            if latest:
                results.append(latest)

        # If empty, run evaluation automatically
        if not results:
            results = await self.evaluate_farm_risks(farm)

        return results

    def get_historical_risks(
        self,
        farm_id,
        limit: int = 50,
        category: Optional[str] = None,
    ) -> List[RiskAssessment]:
        """Retrieves historical risk assessments for a farm."""
        stmt = select(RiskAssessment).where(RiskAssessment.farm_id == farm_id)
        if category:
            stmt = stmt.where(RiskAssessment.risk_category == category)
        stmt = stmt.order_by(desc(RiskAssessment.assessed_at)).limit(limit)
        return list(self.db.scalars(stmt).all())

