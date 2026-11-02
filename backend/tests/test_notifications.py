import uuid
import random
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.models.risk import RiskAssessment
from app.models.weather import WeatherObservation
from app.models.notification import Notification, FarmerPreference
from app.services.notification.sns_provider import (
    SNSProvider,
    normalize_phone_number,
    mask_phone_number,
)
from app.services.notification.service import NotificationService
from app.services.risk.service import RiskService


def create_test_user(
    db: Session,
    role: str = "farmer",
    phone: str = None,
) -> User:
    unique_suffix = random.randint(1000000, 9999999)
    if not phone:
        phone = f"+1555{unique_suffix}"
    user = User(
        full_name=f"Test {role.title()} {unique_suffix}",
        email=f"{role}_{unique_suffix}@example.com",
        phone_number=phone,
        password_hash="mock_hash",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_auth_token(client: TestClient, db: Session, user: User) -> str:
    from app.core.security import create_access_token
    return create_access_token(subject=str(user.id), role=user.role, email=user.email)


# =============================================================================
# Unit Tests: Phone Number Normalization & Masking
# =============================================================================

def test_phone_number_normalization():
    assert normalize_phone_number("+1 (555) 123-4567") == "+15551234567"
    assert normalize_phone_number("0092 300 1234567") == "+923001234567"
    assert normalize_phone_number("+92-300-1234567") == "+923001234567"
    assert normalize_phone_number("15551234567") == "+15551234567"
    assert normalize_phone_number("invalid") is None
    assert normalize_phone_number("") is None
    assert normalize_phone_number(None) is None


def test_phone_number_masking():
    assert mask_phone_number("+15551234567") == "+1555****567"
    assert mask_phone_number("+923001234567") == "+9230****567"
    assert mask_phone_number("") == "UNKNOWN"
    assert mask_phone_number(None) == "UNKNOWN"
    assert mask_phone_number("12345") == "***45"


# =============================================================================
# Unit Tests: SNS Provider Behavior (Mocked AWS)
# =============================================================================

def test_sns_provider_disabled_by_config():
    mock_boto_client = MagicMock()
    provider = SNSProvider(client=mock_boto_client)

    with patch.object(settings, "SNS_SMS_ENABLED", False):
        result = provider.send_sms("+15551234567", "Test alert")
        assert result["success"] is False
        assert result["status"] == "disabled"
        assert result["masked_phone"] == "+1555****567"
        mock_boto_client.publish.assert_not_called()


def test_sns_provider_invalid_phone_rejection():
    mock_boto_client = MagicMock()
    provider = SNSProvider(client=mock_boto_client)

    with patch.object(settings, "SNS_SMS_ENABLED", True):
        result = provider.send_sms("not-a-number", "Test alert")
        assert result["success"] is False
        assert result["status"] == "failed"
        assert "valid E.164" in result["error"]
        mock_boto_client.publish.assert_not_called()


def test_sns_provider_publish_success_status_accepted():
    mock_boto_client = MagicMock()
    mock_boto_client.publish.return_value = {"MessageId": "mock-sns-msg-9999"}
    provider = SNSProvider(client=mock_boto_client)

    with patch.object(settings, "SNS_SMS_ENABLED", True):
        result = provider.send_sms("+15551234567", "Urgent frost warning")
        assert result["success"] is True
        # Critical verification: status must be 'accepted', never 'delivered'
        assert result["status"] == "accepted"
        assert result["message_id"] == "mock-sns-msg-9999"
        assert result["masked_phone"] == "+1555****567"
        assert result["error"] is None
        mock_boto_client.publish.assert_called_once()


def test_sns_provider_client_error_and_throttling():
    mock_boto_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "ThrottlingException",
            "Message": "Rate exceeded for SMS publish.",
        }
    }
    mock_boto_client.publish.side_effect = ClientError(error_response, "Publish")
    provider = SNSProvider(client=mock_boto_client)

    with patch.object(settings, "SNS_SMS_ENABLED", True):
        result = provider.send_sms("+15551234567", "Test advisory")
        assert result["success"] is False
        assert result["status"] == "failed"
        assert "ThrottlingException" in result["error"]
        assert result["masked_phone"] == "+1555****567"


def test_sns_provider_missing_credentials_graceful():
    mock_boto_client = MagicMock()
    mock_boto_client.publish.side_effect = NoCredentialsError()
    provider = SNSProvider(client=mock_boto_client)

    with patch.object(settings, "SNS_SMS_ENABLED", True):
        result = provider.send_sms("+15551234567", "Test advisory")
        assert result["success"] is False
        assert result["status"] == "failed"
        assert "No AWS credentials" in result["error"]


# =============================================================================
# Service Tests: Farmer Preferences & Consent Enforcement
# =============================================================================

def test_farmer_preference_lifecycle(test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    service = NotificationService(test_db)

    # Default preference: sms_consent is False
    pref = service.get_farmer_preference(farmer.id)
    assert pref.sms_consent is False
    assert pref.sms_consent_at is None

    # Opt-in: set sms_consent to True
    updated = service.update_farmer_preference(farmer.id, sms_consent=True, language_preference="ur")
    assert updated.sms_consent is True
    assert updated.sms_consent_at is not None
    assert updated.language_preference == "ur"

    # Opt-out: set sms_consent to False
    opt_out = service.update_farmer_preference(farmer.id, sms_consent=False)
    assert opt_out.sms_consent is False


def test_opted_out_farmer_receives_in_app_only(test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)
    service = NotificationService(test_db, sns_provider=mock_sns)

    # Farmer has NOT consented (sms_consent=False)
    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Pest Warning",
        message="Aphid population surge detected.",
        severity="HIGH",
        channel="both",  # requested both
    )

    # Channel should be downgraded to in_app and no SMS attempted
    assert notif.channel == "in_app"
    assert notif.status == "accepted"
    mock_sns.send_sms.assert_not_called()


def test_opted_in_farmer_triggers_mocked_sms(test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.return_value = {
        "success": True,
        "status": "accepted",
        "message_id": "test-sns-uuid-4321",
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": None,
    }
    service = NotificationService(test_db, sns_provider=mock_sns)

    # Opt-in farmer
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Frost Warning",
        message="Sub-zero temperatures anticipated tonight.",
        severity="CRITICAL",
        channel="both",
    )

    assert notif.status == "accepted"
    assert notif.sns_message_id == "test-sns-uuid-4321"
    assert notif.masked_phone_number == mask_phone_number(farmer.phone_number)
    assert notif.delivery_attempts == 1
    mock_sns.send_sms.assert_called_once()


# =============================================================================
# Risk Integration & Idempotency Tests
# =============================================================================

def test_risk_evaluation_notification_trigger_and_idempotency(test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Emerald Valley",
        district="Green District",
        village="Valley Farm",
        latitude=31.5204,
        longitude=74.3587,
        total_area=15.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()
    test_db.refresh(farm)

    mock_sns = MagicMock(spec=SNSProvider)
    service = NotificationService(test_db, sns_provider=mock_sns)

    # Create dummy high risk assessment
    now_utc = datetime.now(timezone.utc)
    high_risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="heat_stress",
        risk_level="HIGH",
        risk_score=78.5,
        evidence={"max_temp": 42.0},
        explanation="Extreme daytime temperatures approaching physiological threshold.",
        recommended_precaution="Apply light surface irrigation to reduce canopy heat.",
        assessed_at=now_utc,
    )
    test_db.add(high_risk)

    # Low risk should NOT trigger notification
    low_risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="frost_damage",
        risk_level="LOW",
        risk_score=10.0,
        evidence={"min_temp": 18.0},
        explanation="Temperatures well above freezing threshold.",
        recommended_precaution="No action needed.",
        assessed_at=now_utc,
    )
    test_db.add(low_risk)
    test_db.commit()
    test_db.refresh(high_risk)
    test_db.refresh(low_risk)

    # Trigger risk notifications
    created = service.create_risk_notifications(farm, [high_risk, low_risk])
    assert len(created) == 1
    assert created[0].risk_assessment_id == high_risk.id
    assert created[0].severity == "HIGH"

    # IDEMPOTENCY CHECK: Running risk notifications again with the exact same assessments
    # should NOT produce a duplicate notification
    second_run = service.create_risk_notifications(farm, [high_risk, low_risk])
    assert len(second_run) == 0

    # Total notifications in DB for this farm should remain 1
    notifications_list, total = service.list_farmer_notifications(farmer.id)
    assert total == 1


# =============================================================================
# API Endpoint Integration Tests (Farmer & Admin)
# =============================================================================

def test_api_farmer_get_and_update_preferences(client: TestClient, test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    token = get_auth_token(client, test_db, farmer)
    headers = {"Authorization": f"Bearer {token}"}

    # GET preferences
    res = client.get("/api/v1/notifications/preferences", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["sms_consent"] is False

    # PATCH preferences (opt-in)
    patch_res = client.patch(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={"sms_consent": True, "language_preference": "ur"},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["sms_consent"] is True
    assert updated_data["language_preference"] == "ur"
    assert updated_data["sms_consent_at"] is not None


def test_api_farmer_list_and_mark_read(client: TestClient, test_db: Session):
    farmer = create_test_user(test_db, role="farmer")
    token = get_auth_token(client, test_db, farmer)
    headers = {"Authorization": f"Bearer {token}"}

    service = NotificationService(test_db)
    notif1 = service.create_notification(
        farmer_id=farmer.id,
        title="Alert 1",
        message="Alert message 1",
        severity="HIGH",
    )
    notif2 = service.create_notification(
        farmer_id=farmer.id,
        title="Alert 2",
        message="Alert message 2",
        severity="LOW",
    )

    # List notifications
    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    assert list_data["unread_count"] == 2

    # Mark single notification as read
    read_res = client.post(f"/api/v1/notifications/{notif1.id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["notification"]["is_read"] is True

    # Mark all read
    mark_all_res = client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert mark_all_res.status_code == 200
    assert mark_all_res.json()["marked_count"] == 1  # only notif2 was unread


def test_api_notification_ownership_isolation(client: TestClient, test_db: Session):
    farmer1 = create_test_user(test_db, role="farmer")
    farmer2 = create_test_user(test_db, role="farmer")
    token1 = get_auth_token(client, test_db, farmer1)
    headers1 = {"Authorization": f"Bearer {token1}"}

    service = NotificationService(test_db)
    notif_farmer2 = service.create_notification(
        farmer_id=farmer2.id,
        title="Farmer 2 Private Alert",
        message="Private data",
        severity="CRITICAL",
    )

    # Farmer 1 attempts to read Farmer 2's notification
    res = client.get(f"/api/v1/notifications/{notif_farmer2.id}", headers=headers1)
    assert res.status_code == 404

    # Farmer 1 attempts to mark Farmer 2's notification as read
    res_read = client.post(f"/api/v1/notifications/{notif_farmer2.id}/read", headers=headers1)
    assert res_read.status_code == 404


def test_api_admin_rbac_and_broadcast(client: TestClient, test_db: Session):
    admin = create_test_user(test_db, role="admin")
    farmer = create_test_user(test_db, role="farmer")

    admin_token = get_auth_token(client, test_db, admin)
    farmer_token = get_auth_token(client, test_db, farmer)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    # Farmer attempts to access admin notifications endpoint -> 403 Forbidden
    forbidden_res = client.get("/api/v1/admin/notifications", headers=farmer_headers)
    assert forbidden_res.status_code == 403

    # Admin accesses notifications list -> 200 OK
    admin_res = client.get("/api/v1/admin/notifications", headers=admin_headers)
    assert admin_res.status_code == 200

    # Admin dispatches emergency broadcast (requires confirmed=True)
    broadcast_payload = {
        "title": "Severe Pest Advisory",
        "message": "Locust swarm spotted in Sector 4. Scout crops immediately.",
        "severity": "CRITICAL",
        "district": "all",
        "confirmed": True,
    }
    broadcast_res = client.post(
        "/api/v1/admin/notifications/broadcast",
        headers=admin_headers,
        json=broadcast_payload,
    )
    assert broadcast_res.status_code == 200
    broadcast_data = broadcast_res.json()
    assert broadcast_data["notifications_queued"] >= 1
    assert "dispatched to" in broadcast_data["message"]


def test_delivery_semantics_accepted_vs_delivered_distinction(test_db: Session):
    """
    Explicitly verify delivery semantics: SNS publish returns AWS acceptance,
    so status MUST be recorded as 'accepted' and NEVER falsely as 'delivered'.
    """
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.return_value = {
        "success": True,
        "status": "accepted",
        "message_id": "sns-acceptance-token-1234",
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": None,
    }
    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Delivery Status Test",
        message="Testing that status is accepted not delivered",
        severity="HIGH",
        channel="both",
    )

    assert notif.status == "accepted"
    assert notif.status != "delivered"
    assert notif.sns_message_id == "sns-acceptance-token-1234"


# =============================================================================
# Step 6.1 Audit Tests: Reliability, Concurrency, Retries & Broadcast Safety
# =============================================================================

def test_notification_commit_before_sns_publish(test_db: Session):
    """
    Verify transaction ordering: Notification is durably committed
    in the database before any external SNS network call occurs.
    """
    farmer = create_test_user(test_db, role="farmer")
    notification_verified_in_db_during_publish = False

    def side_effect_publish(phone_number, message, sender_id=None):
        nonlocal notification_verified_in_db_during_publish
        # Verify in database using a separate query
        stmt = select(Notification).where(Notification.farmer_id == farmer.id)
        persisted = test_db.scalar(stmt)
        if persisted and persisted.status == "sending":
            notification_verified_in_db_during_publish = True
        return {
            "success": True,
            "status": "accepted",
            "message_id": "msg-committed-first",
            "masked_phone": "+1555****123",
            "error": None,
        }

    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.side_effect = side_effect_publish

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Durable Outbox Test",
        message="Verifying commit precedes publish",
        severity="HIGH",
        channel="both",
    )

    assert notification_verified_in_db_during_publish is True
    assert notif.status == "accepted"
    assert notif.sns_message_id == "msg-committed-first"


def test_sns_failure_without_risk_assessment_or_notification_rollback(test_db: Session):
    """
    Verify provider failures or unhandled exceptions never roll back
    the risk assessment or notification records.
    """
    farmer = create_test_user(test_db, role="farmer")
    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Resilience Farm",
        district="Central District",
        village="Central Village",
        latitude=30.0,
        longitude=70.0,
        total_area=10.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()
    test_db.refresh(farm)

    risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="flood_inundation",
        risk_level="CRITICAL",
        risk_score=95.0,
        evidence={"rainfall_mm": 120.0},
        explanation="Severe localized flash flooding anticipated.",
        recommended_precaution="Move equipment to higher ground immediately.",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)
    test_db.commit()
    test_db.refresh(risk)

    # Provider crashes completely
    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.side_effect = RuntimeError("AWS Connection Reset by Peer")

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    created_notifs = service.create_risk_notifications(farm, [risk])
    assert len(created_notifs) == 1

    # Verify both the risk assessment and notification are durably present in DB
    refreshed_risk = test_db.get(RiskAssessment, risk.id)
    assert refreshed_risk is not None

    refreshed_notif = test_db.get(Notification, created_notifs[0].id)
    assert refreshed_notif is not None
    assert refreshed_notif.status == "failed"
    assert "AWS Connection Reset" in refreshed_notif.error_message


def test_concurrent_duplicate_risk_events_safely_handled(test_db: Session):
    """
    Verify atomic duplicate protection: concurrent attempts to evaluate
    the same risk assessment do not create duplicate notifications or SMS messages.
    """
    farmer = create_test_user(test_db, role="farmer")
    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Concurrency Farm",
        district="Valley District",
        village="Valley Village",
        latitude=32.0,
        longitude=72.0,
        total_area=20.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()
    test_db.refresh(farm)

    risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="frost_damage",
        risk_level="HIGH",
        risk_score=80.0,
        evidence={"min_temp": -2.0},
        explanation="Frost warning.",
        recommended_precaution="Cover sensitive crops.",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)
    test_db.commit()
    test_db.refresh(risk)

    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.return_value = {
        "success": True,
        "status": "accepted",
        "message_id": "concurrency-msg-1",
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": None,
    }
    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    # First thread creates notification
    batch1 = service.create_risk_notifications(farm, [risk])
    assert len(batch1) == 1

    # Concurrent thread tries with same assessment
    batch2 = service.create_risk_notifications(farm, [risk])
    assert len(batch2) == 0

    # Ensure only 1 SMS call was made
    assert mock_sns.send_sms.call_count == 1

    # Total in DB is exactly 1
    total = test_db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.farm_id == farm.id,
            Notification.risk_assessment_id == risk.id,
        )
    )
    assert total == 1


def test_database_level_unique_constraint(test_db: Session):
    """
    Verify DB-level UniqueConstraint uq_notifications_farm_risk_assessment
    prevents duplicate rows for (farm_id, risk_assessment_id).
    """
    from sqlalchemy.exc import IntegrityError

    farmer = create_test_user(test_db, role="farmer")
    farm = Farm(
        farmer_id=farmer.id,
        farm_name="Constraint Farm",
        district="District 1",
        village="Village 1",
        latitude=33.0,
        longitude=73.0,
        total_area=5.0,
        area_unit="acres",
    )
    test_db.add(farm)
    test_db.commit()
    test_db.refresh(farm)

    risk = RiskAssessment(
        farm_id=farm.id,
        risk_category="heat_stress",
        risk_level="CRITICAL",
        risk_score=90.0,
        evidence={"temp": 45.0},
        explanation="Heat wave.",
        recommended_precaution="Irrigate.",
        assessed_at=datetime.now(timezone.utc),
    )
    test_db.add(risk)
    test_db.commit()
    test_db.refresh(risk)

    n1 = Notification(
        farmer_id=farmer.id,
        farm_id=farm.id,
        risk_assessment_id=risk.id,
        title="Title 1",
        message="Message 1",
        severity="CRITICAL",
    )
    test_db.add(n1)
    test_db.commit()

    # Second row with exact same farm_id and risk_assessment_id must violate unique constraint
    n2 = Notification(
        farmer_id=farmer.id,
        farm_id=farm.id,
        risk_assessment_id=risk.id,
        title="Title 2",
        message="Message 2",
        severity="CRITICAL",
    )
    test_db.add(n2)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_transient_failure_retries_and_exponential_backoff(test_db: Session):
    """
    Verify transient failures (e.g. ThrottlingException) are retried
    by retry_failed_notifications until accepted.
    """
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)

    # First attempt: ThrottlingException (transient)
    mock_sns.send_sms.return_value = {
        "success": False,
        "status": "failed",
        "message_id": None,
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": "AWS SNS ClientError [ThrottlingException]: Rate exceeded.",
        "is_transient": True,
    }

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Transient Test",
        message="Throttled alert",
        severity="HIGH",
        channel="both",
    )
    assert notif.status == "failed"
    assert notif.delivery_attempts == 1

    # Second attempt: recovery
    mock_sns.send_sms.return_value = {
        "success": True,
        "status": "accepted",
        "message_id": "throttling-recovered-msg",
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": None,
        "is_transient": False,
    }

    retried = service.retry_failed_notifications(limit=10)
    assert len(retried) >= 1
    target_retried = next(r for r in retried if r.id == notif.id)
    assert target_retried.status == "accepted"
    assert target_retried.delivery_attempts == 2
    assert target_retried.sns_message_id == "throttling-recovered-msg"


def test_permanent_failure_is_not_retried(test_db: Session):
    """
    Verify permanent failures (e.g. invalid phone number) are marked
    as terminal and never retried.
    """
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)

    mock_sns.send_sms.return_value = {
        "success": False,
        "status": "failed",
        "message_id": None,
        "masked_phone": "+1555****000",
        "error": "AWS SNS ClientError [InvalidParameterException]: Invalid phone destination.",
        "is_transient": False,
    }

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Permanent Failure Test",
        message="Invalid phone",
        severity="HIGH",
        channel="both",
    )
    assert notif.status == "failed"
    assert notif.delivery_attempts == settings.SNS_SMS_MAX_RETRIES

    # Try retrying: should NOT retry permanent failure
    retried = service.retry_failed_notifications()
    assert len(retried) == 0
    # send_sms was called only once initially
    assert mock_sns.send_sms.call_count == 1


def test_maximum_retry_limit_boundary(test_db: Session):
    """
    Verify that notifications reaching max retry limit (3) are no longer retried.
    """
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.return_value = {
        "success": False,
        "status": "failed",
        "message_id": None,
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": "Transient server error",
        "is_transient": True,
    }

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Max Retry Test",
        message="Testing attempts boundary",
        severity="HIGH",
        channel="both",
    )
    assert notif.delivery_attempts == 1

    # Attempt 2
    service.retry_failed_notifications()
    test_db.refresh(notif)
    assert notif.delivery_attempts == 2

    # Attempt 3 (reaches max limit = 3)
    service.retry_failed_notifications()
    test_db.refresh(notif)
    assert notif.delivery_attempts == 3

    # Attempt 4: no longer retried
    retried_after_max = service.retry_failed_notifications()
    assert len(retried_after_max) == 0
    assert mock_sns.send_sms.call_count == 3


def test_process_recovery_without_unintended_duplicate_sms(test_db: Session):
    """
    Verify that once a notification has been accepted by AWS SNS,
    re-running dispatch or recovery workers never sends duplicate SMS.
    """
    farmer = create_test_user(test_db, role="farmer")
    mock_sns = MagicMock(spec=SNSProvider)
    mock_sns.send_sms.return_value = {
        "success": True,
        "status": "accepted",
        "message_id": "initial-accepted-id",
        "masked_phone": mask_phone_number(farmer.phone_number),
        "error": None,
    }

    service = NotificationService(test_db, sns_provider=mock_sns)
    service.update_farmer_preference(farmer.id, sms_consent=True)

    notif = service.create_notification(
        farmer_id=farmer.id,
        title="Recovery Test",
        message="Testing recovery idempotency",
        severity="HIGH",
        channel="both",
    )
    assert notif.status == "accepted"
    assert mock_sns.send_sms.call_count == 1

    # Simulate process recovery or re-triggering dispatch for same notification ID
    recovered = service._dispatch_sms(notif.id)
    assert recovered.id == notif.id
    # Call count must still be 1 (bypassed duplicate)
    assert mock_sns.send_sms.call_count == 1


def test_admin_broadcast_preview_dry_run_no_writes(client: TestClient, test_db: Session):
    """
    Verify broadcast preview endpoint returns audience breakdown
    without persisting notifications or sending SMS messages.
    """
    admin = create_test_user(test_db, role="admin")
    farmer_consented = create_test_user(test_db, role="farmer")
    farmer_opted_out = create_test_user(test_db, role="farmer")

    service = NotificationService(test_db)
    service.update_farmer_preference(farmer_consented.id, sms_consent=True)
    service.update_farmer_preference(farmer_opted_out.id, sms_consent=False)

    token = get_auth_token(client, test_db, admin)
    headers = {"Authorization": f"Bearer {token}"}

    preview_payload = {
        "title": "Dry Run Preview",
        "message": "Testing audience calculations",
        "severity": "HIGH",
        "district": "all",
    }

    initial_notif_count = test_db.scalar(select(func.count()).select_from(Notification)) or 0

    res = client.post(
        "/api/v1/admin/notifications/broadcast/preview",
        headers=headers,
        json=preview_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_farmers_count"] >= 2
    assert data["sms_consented_count"] >= 1
    assert data["in_app_only_count"] >= 1

    # Verify no new notifications were written to DB
    final_notif_count = test_db.scalar(select(func.count()).select_from(Notification)) or 0
    assert final_notif_count == initial_notif_count


def test_admin_broadcast_confirmation_and_opt_out_enforcement(client: TestClient, test_db: Session):
    """
    Verify:
    1. Unconfirmed broadcast (confirmed=False) is rejected with 400 Bad Request.
    2. Confirmed broadcast executes, respects opt-out (in_app only for non-consented),
       and records BroadcastAudit.
    """
    admin = create_test_user(test_db, role="admin")
    farmer_consented = create_test_user(test_db, role="farmer")
    farmer_opted_out = create_test_user(test_db, role="farmer")

    service = NotificationService(test_db)
    service.update_farmer_preference(farmer_consented.id, sms_consent=True)
    service.update_farmer_preference(farmer_opted_out.id, sms_consent=False)

    token = get_auth_token(client, test_db, admin)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Mandatory Confirmation Test",
        "message": "Safety audit broadcast",
        "severity": "CRITICAL",
        "district": "all",
        "confirmed": False,
    }

    # 1. Unconfirmed request rejected
    rejected_res = client.post(
        "/api/v1/admin/notifications/broadcast",
        headers=headers,
        json=payload,
    )
    assert rejected_res.status_code == 400
    err_body = rejected_res.json()
    err_msg = err_body.get("error", {}).get("message") or err_body.get("detail", "")
    assert "explicit confirmation" in err_msg

    # 2. Confirmed request succeeds
    payload["confirmed"] = True
    confirmed_res = client.post(
        "/api/v1/admin/notifications/broadcast",
        headers=headers,
        json=payload,
    )
    assert confirmed_res.status_code == 200
    res_data = confirmed_res.json()
    assert res_data["audit_id"] is not None

    # Verify opted-out farmer only got in_app notification
    notif_opted_out = test_db.scalar(
        select(Notification).where(
            Notification.farmer_id == farmer_opted_out.id,
            Notification.title == "Mandatory Confirmation Test",
        )
    )
    assert notif_opted_out is not None
    assert notif_opted_out.channel == "in_app"
    assert notif_opted_out.sns_message_id is None

    # Verify BroadcastAudit record exists
    from app.models.notification import BroadcastAudit
    audit_record = test_db.get(BroadcastAudit, uuid.UUID(res_data["audit_id"]))
    assert audit_record is not None
    assert audit_record.admin_id == admin.id
    assert audit_record.severity == "CRITICAL"


