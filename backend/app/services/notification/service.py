import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.user import User
from app.models.farm import Farm
from app.models.risk import RiskAssessment
from app.models.notification import Notification, FarmerPreference, BroadcastAudit
from app.services.notification.sns_provider import (
    SNSProvider,
    mask_phone_number,
    normalize_phone_number,
)

logger = logging.getLogger("farmshield.notification.service")


class NotificationService:
    def __init__(self, db: Session, sns_provider: Optional[SNSProvider] = None):
        self.db = db
        self.sns = sns_provider or SNSProvider()

    def get_farmer_preference(self, user_id: uuid.UUID) -> FarmerPreference:
        """Retrieves or initializes the notification preferences for a farmer."""
        stmt = select(FarmerPreference).where(FarmerPreference.user_id == user_id)
        pref = self.db.scalar(stmt)
        if not pref:
            pref = FarmerPreference(
                user_id=user_id,
                sms_consent=False,
                language_preference="en",
            )
            self.db.add(pref)
            self.db.commit()
            self.db.refresh(pref)
        return pref

    def update_farmer_preference(
        self,
        user_id: uuid.UUID,
        sms_consent: bool,
        language_preference: Optional[str] = None,
    ) -> FarmerPreference:
        """Updates SMS consent and notification preferences with timestamp auditing."""
        pref = self.get_farmer_preference(user_id)
        now_utc = datetime.now(timezone.utc)

        if sms_consent and not pref.sms_consent:
            pref.sms_consent_at = now_utc
        elif not sms_consent:
            pref.sms_consent_at = now_utc

        pref.sms_consent = sms_consent
        if language_preference:
            pref.language_preference = language_preference
        pref.updated_at = now_utc

        self.db.commit()
        self.db.refresh(pref)
        logger.info(
            f"Updated notification preferences for user {user_id}: sms_consent={sms_consent}"
        )
        return pref

    def _dispatch_sms(self, notification_id: uuid.UUID) -> Optional[Notification]:
        """
        Executes bounded, reliable SMS dispatch for an existing, committed notification.
        Idempotent: prevents duplicate SMS dispatch if already accepted or max retries exceeded.
        """
        notification = self.db.get(Notification, notification_id)
        if not notification:
            return None

        # Process recovery / Duplicate check: If already accepted by AWS SNS, do NOT send again
        if notification.status == "accepted" and notification.sns_message_id:
            logger.debug(
                f"Notification {notification_id} already has accepted SNS MessageId {notification.sns_message_id}. Skipping duplicate SMS dispatch."
            )
            return notification

        # Check maximum retry boundary
        if notification.delivery_attempts >= settings.SNS_SMS_MAX_RETRIES:
            logger.warning(
                f"Notification {notification_id} exceeded max delivery attempts ({notification.delivery_attempts}/{settings.SNS_SMS_MAX_RETRIES}). Terminal failure."
            )
            notification.status = "failed"
            self.db.commit()
            self.db.refresh(notification)
            return notification

        # Verify farmer consent
        pref = self.get_farmer_preference(notification.farmer_id)
        if not pref.sms_consent:
            logger.info(
                f"Farmer {notification.farmer_id} has not granted SMS consent. SMS dispatch skipped. Notification channel is in_app."
            )
            notification.channel = "in_app"
            notification.status = "accepted"
            self.db.commit()
            self.db.refresh(notification)
            return notification

        farmer = self.db.get(User, notification.farmer_id)
        if not farmer:
            notification.status = "failed"
            notification.error_message = "Farmer user record not found"
            self.db.commit()
            self.db.refresh(notification)
            return notification

        raw_phone = farmer.phone_number
        norm_phone = normalize_phone_number(raw_phone)
        masked = mask_phone_number(norm_phone or raw_phone)
        notification.masked_phone_number = masked

        # Permanent failure check: invalid phone number cannot be retried
        if not norm_phone:
            notification.status = "failed"
            notification.delivery_attempts = settings.SNS_SMS_MAX_RETRIES
            notification.error_message = f"Farmer phone number {masked} cannot be formatted to valid E.164."
            self.db.commit()
            self.db.refresh(notification)
            return notification

        # Update attempt counter & state to 'sending' before network call
        notification.delivery_attempts += 1
        now_utc = datetime.now(timezone.utc)
        notification.last_attempt_at = now_utc
        notification.status = "sending"
        self.db.commit()
        self.db.refresh(notification)

        sms_body = f"FarmShield [{notification.severity} Alert]: {notification.title}\n{notification.message}\nView: {settings.FARMSHIELD_DASHBOARD_URL}"
        if len(sms_body) > 300:
            sms_body = sms_body[:297] + "..."

        try:
            dispatch_result = self.sns.send_sms(
                phone_number=norm_phone,
                message=sms_body,
            )

            if dispatch_result["success"]:
                notification.status = "accepted"
                notification.sns_message_id = dispatch_result.get("message_id")
                notification.error_message = None
            else:
                is_transient = dispatch_result.get("is_transient", False)
                if not is_transient or notification.delivery_attempts >= settings.SNS_SMS_MAX_RETRIES:
                    notification.status = "failed"
                    # Terminal failure: mark attempts to max so it is not retried
                    notification.delivery_attempts = max(
                        notification.delivery_attempts, settings.SNS_SMS_MAX_RETRIES
                    )
                else:
                    # Transient error: mark failed with remaining retry eligibility
                    notification.status = "failed"

                notification.error_message = dispatch_result.get("error")

        except Exception as exc:
            logger.exception(f"Unexpected provider error during SMS dispatch: {exc}")
            notification.status = "failed"
            notification.error_message = f"Provider error: {type(exc).__name__}: {str(exc)}"

        self.db.commit()
        self.db.refresh(notification)
        return notification

    def create_notification(
        self,
        farmer_id: uuid.UUID,
        title: str,
        message: str,
        severity: str = "LOW",
        notification_type: str = "risk_alert",
        farm_id: Optional[uuid.UUID] = None,
        risk_assessment_id: Optional[uuid.UUID] = None,
        channel: str = "in_app",
    ) -> Notification:
        """
        Durably commits an in-app notification first, ensuring transaction safety.
        Only after durable persistence is external SMS dispatch attempted.
        Provider failures never roll back the created notification.
        """
        farmer = self.db.get(User, farmer_id)
        if not farmer:
            raise ValueError(f"Farmer with id {farmer_id} not found.")

        # Stage 1: Durably commit the in-app notification
        notification = Notification(
            farmer_id=farmer_id,
            farm_id=farm_id,
            risk_assessment_id=risk_assessment_id,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            channel=channel,
            is_read=False,
            status="pending",
            delivery_attempts=0,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # Stage 2: Outbox dispatch if channel includes SMS
        if channel in ("sms", "both"):
            pref = self.get_farmer_preference(farmer_id)
            if pref.sms_consent:
                self._dispatch_sms(notification.id)
            else:
                # Downgrade to in-app accepted
                notification.channel = "in_app"
                notification.status = "accepted"
                self.db.commit()
                self.db.refresh(notification)
        else:
            notification.status = "accepted"
            self.db.commit()
            self.db.refresh(notification)

        return notification

    def create_risk_notifications(
        self,
        farm: Farm,
        assessments: List[RiskAssessment],
    ) -> List[Notification]:
        """
        Evaluates risk assessments and triggers notifications for HIGH and CRITICAL risks.
        Applies atomic duplicate protection: uses database unique constraint
        and transaction savepoints to prevent race conditions during concurrent evaluations.
        """
        created_notifications: List[Notification] = []

        urgent_assessments = [
            a for a in assessments if a.risk_level in ("HIGH", "CRITICAL")
        ]

        if not urgent_assessments:
            return created_notifications

        pref = self.get_farmer_preference(farm.farmer_id)
        channel = "both" if pref.sms_consent else "in_app"

        for assessment in urgent_assessments:
            # Check existing first
            existing_stmt = select(Notification).where(
                Notification.farm_id == farm.id,
                Notification.risk_assessment_id == assessment.id,
            )
            existing = self.db.scalar(existing_stmt)
            if existing:
                logger.debug(
                    f"Notification already exists for farm {farm.id} and risk {assessment.id}. Skipping duplicate."
                )
                continue

            category_name = assessment.risk_category.replace("_", " ").title()
            title = f"{assessment.risk_level} Risk: {category_name} Alert"
            message = (
                f"{assessment.explanation[:120]}... "
                f"Action recommended: {assessment.recommended_precaution[:100]}"
            )

            # Atomic insertion protected by savepoint and uq_notifications_farm_risk_assessment
            notif = None
            try:
                with self.db.begin_nested():
                    # Double-check inside savepoint
                    existing_in_tx = self.db.scalar(existing_stmt)
                    if existing_in_tx:
                        continue

                    new_notif = Notification(
                        farmer_id=farm.farmer_id,
                        farm_id=farm.id,
                        risk_assessment_id=assessment.id,
                        notification_type="risk_alert",
                        title=title,
                        message=message,
                        severity=assessment.risk_level,
                        channel=channel,
                        is_read=False,
                        status="pending",
                        delivery_attempts=0,
                    )
                    self.db.add(new_notif)
                    self.db.flush()
                    notif = new_notif

                # Commit durable state
                self.db.commit()
                self.db.refresh(notif)
            except IntegrityError:
                # Concurrent race condition caught safely! Another thread already created this notification.
                self.db.rollback()
                logger.info(
                    f"Concurrent duplicate prevented by DB unique constraint for farm {farm.id}, risk {assessment.id}."
                )
                continue
            except Exception as exc:
                self.db.rollback()
                logger.error(
                    f"Failed to persist risk notification for farm {farm.id}, assessment {assessment.id}: {exc}"
                )
                continue

            if notif:
                # Outbox SMS dispatch
                if channel in ("sms", "both"):
                    self._dispatch_sms(notif.id)
                else:
                    notif.status = "accepted"
                    self.db.commit()
                    self.db.refresh(notif)

                created_notifications.append(notif)

        return created_notifications

    def retry_failed_notifications(self, limit: int = 20) -> List[Notification]:
        """
        Retries pending or transiently failed SMS notifications with bounded attempts.
        Does not retry permanent failures.
        """
        stmt = (
            select(Notification)
            .where(
                Notification.channel.in_(["sms", "both"]),
                Notification.status.in_(["pending", "failed"]),
                Notification.delivery_attempts < settings.SNS_SMS_MAX_RETRIES,
                Notification.sns_message_id.is_(None),
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        candidates = list(self.db.scalars(stmt).all())
        retried: List[Notification] = []

        for notif in candidates:
            updated = self._dispatch_sms(notif.id)
            if updated:
                retried.append(updated)

        return retried

    def list_farmer_notifications(
        self,
        farmer_id: uuid.UUID,
        farm_id: Optional[uuid.UUID] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int]:
        """Lists notifications belonging to a farmer with pagination and optional filtering."""
        query = select(Notification).where(Notification.farmer_id == farmer_id)

        if farm_id:
            query = query.where(Notification.farm_id == farm_id)

        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        paged_query = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit)
        items = list(self.db.scalars(paged_query).all())

        return items, total

    def get_notification(
        self, farmer_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        """Retrieves a specific notification belonging to the farmer."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.farmer_id == farmer_id,
        )
        return self.db.scalar(stmt)

    def mark_as_read(
        self, farmer_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        """Marks a notification as read if owned by the farmer."""
        notif = self.get_notification(farmer_id, notification_id)
        if notif and not notif.is_read:
            notif.is_read = True
            notif.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(notif)
        return notif

    def mark_all_as_read(self, farmer_id: uuid.UUID) -> int:
        """Marks all unread notifications for a farmer as read."""
        stmt = select(Notification).where(
            Notification.farmer_id == farmer_id,
            Notification.is_read.is_(False),
        )
        unread_notifications = list(self.db.scalars(stmt).all())
        now_utc = datetime.now(timezone.utc)
        for n in unread_notifications:
            n.is_read = True
            n.updated_at = now_utc

        self.db.commit()
        return len(unread_notifications)

    def list_admin_notifications(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int]:
        """Admin query across all notifications in the system."""
        query = select(Notification)

        if severity:
            query = query.where(Notification.severity == severity.upper())

        if status:
            query = query.where(Notification.status == status.lower())

        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        paged_query = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit)
        items = list(self.db.scalars(paged_query).all())
        return items, total

    def _get_target_farmers(self, district: Optional[str] = None) -> List[User]:
        """Helper to retrieve eligible target farmers for a broadcast."""
        if district and district.lower() not in ("all", "all districts", "all enrolled sectors", "all enrolled districts"):
            stmt = select(User).join(Farm, Farm.farmer_id == User.id).where(
                Farm.district.ilike(f"%{district}%"),
                User.role == "farmer",
            ).distinct()
        else:
            stmt = select(User).where(User.role == "farmer")
        return list(self.db.scalars(stmt).all())

    def preview_admin_broadcast(
        self,
        title: str,
        message: str,
        severity: str,
        district: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dry-run preview: calculates target audience and SMS consent breakdown without sending.
        """
        target_farmers = self._get_target_farmers(district)
        sms_consented_count = 0
        in_app_only_count = 0

        for farmer in target_farmers:
            pref = self.get_farmer_preference(farmer.id)
            if pref.sms_consent:
                sms_consented_count += 1
            else:
                in_app_only_count += 1

        return {
            "target_farmers_count": len(target_farmers),
            "sms_consented_count": sms_consented_count,
            "in_app_only_count": in_app_only_count,
            "district": district,
            "severity": severity,
            "title": title,
            "message": message,
        }

    def admin_broadcast(
        self,
        title: str,
        message: str,
        severity: str,
        district: Optional[str] = None,
        admin_id: Optional[uuid.UUID] = None,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Dispatches emergency broadcast advisory to farmers.
        Requires explicit confirmation (confirmed=True).
        Never bypasses farmer opt-out preferences.
        Records an audit log entry in broadcast_audits table.
        """
        if not confirmed:
            raise ValueError(
                "Broadcast execution requires explicit admin confirmation (confirmed=True). Preview first with /preview."
            )

        target_farmers = self._get_target_farmers(district)

        queued_count = 0
        sms_accepted_count = 0
        sms_failed_count = 0
        sms_consented_count = 0

        for farmer in target_farmers:
            pref = self.get_farmer_preference(farmer.id)
            # Never bypass opt-out preferences!
            channel = "both" if pref.sms_consent else "in_app"
            if pref.sms_consent:
                sms_consented_count += 1

            notif = self.create_notification(
                farmer_id=farmer.id,
                title=title,
                message=message,
                severity=severity,
                notification_type="broadcast",
                channel=channel,
            )
            queued_count += 1
            if channel == "both":
                if notif.status == "accepted" and notif.sns_message_id:
                    sms_accepted_count += 1
                else:
                    sms_failed_count += 1

        # Create persistent audit record
        audit = BroadcastAudit(
            admin_id=admin_id,
            title=title,
            message=message,
            severity=severity,
            district=district,
            target_farmers_count=len(target_farmers),
            sms_consented_count=sms_consented_count,
            notifications_queued=queued_count,
            sms_accepted_count=sms_accepted_count,
            sms_failed_count=sms_failed_count,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)

        return {
            "audit_id": audit.id,
            "target_farmers_count": len(target_farmers),
            "notifications_queued": queued_count,
            "sms_accepted_count": sms_accepted_count,
            "sms_skipped_or_failed_count": (len(target_farmers) - sms_accepted_count),
        }
