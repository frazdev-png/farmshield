import re
import logging
from typing import Optional, Dict, Any
import boto3
import botocore.exceptions
from app.core.config import settings

logger = logging.getLogger("farmshield.notification.sns")


def normalize_phone_number(phone: str) -> Optional[str]:
    """
    Normalizes a phone number to standard E.164 format (e.g., +15551234567, +923001234567).
    Returns None if the phone number cannot be converted to a valid E.164 format.
    """
    if not phone or not isinstance(phone, str):
        return None

    cleaned = phone.strip()
    # Remove whitespace, hyphens, parentheses, and dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", cleaned)

    # If it starts with 00, replace with +
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    # Valid E.164: starts with +, followed by 7 to 15 digits
    e164_pattern = r"^\+[1-9]\d{6,14}$"
    if re.match(e164_pattern, cleaned):
        return cleaned

    return None


TRANSIENT_ERROR_CODES = {
    "Throttling",
    "ThrottlingException",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "EndpointDisabled",
}


def mask_phone_number(phone: Optional[str]) -> str:
    """
    Masks a phone number for audit logging and privacy display (e.g., '+1555****567').
    Never exposes raw phone digits in logs or public responses.
    """
    if not phone:
        return "UNKNOWN"

    phone_str = str(phone).strip()
    if len(phone_str) <= 6:
        return "***" + phone_str[-2:] if len(phone_str) >= 2 else "***"

    prefix = phone_str[:5]
    suffix = phone_str[-3:]
    return f"{prefix}****{suffix}"


class SNSProvider:
    """
    AWS Simple Notification Service (SNS) SMS Provider.
    Implements production-grade error handling, phone normalization, masking,
    and distinct 'accepted' delivery status semantics.
    """

    def __init__(self, client: Optional[Any] = None):
        self._client = client
        self._initialized = False

    @property
    def client(self) -> Optional[Any]:
        if self._client is not None:
            return self._client

        if not self._initialized:
            try:
                self._client = boto3.client("sns", region_name=settings.AWS_REGION)
            except Exception as e:
                logger.warning(
                    f"AWS SNS client initialization error: {e}. SNS features will be disabled or mocked."
                )
                self._client = None
            self._initialized = True

        return self._client

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an SMS message to the specified phone number using AWS SNS.
        
        Returns:
            Dict containing:
                success: bool
                status: 'accepted' | 'failed' | 'disabled'
                message_id: Optional[str]
                masked_phone: str
                error: Optional[str]
        """
        norm_phone = normalize_phone_number(phone_number)
        masked = mask_phone_number(norm_phone or phone_number)

        if not norm_phone:
            err_msg = f"Invalid phone number format for destination: {masked}. Must be valid E.164."
            logger.warning(err_msg)
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "masked_phone": masked,
                "error": err_msg,
                "is_transient": False,
            }

        if not settings.SNS_SMS_ENABLED:
            logger.info(
                f"SNS SMS dispatch skipped for {masked}: SNS_SMS_ENABLED is set to False."
            )
            return {
                "success": False,
                "status": "disabled",
                "message_id": None,
                "masked_phone": masked,
                "error": "SMS notifications are disabled by system configuration (SNS_SMS_ENABLED=False).",
                "is_transient": False,
            }

        sns_client = self.client
        if sns_client is None:
            err_msg = "AWS SNS client is unavailable (missing credentials or client init failed)."
            logger.warning(err_msg)
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "masked_phone": masked,
                "error": err_msg,
                "is_transient": False,
            }

        effective_sender_id = sender_id or settings.SNS_SMS_SENDER_ID
        attributes: Dict[str, Any] = {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": settings.SNS_SMS_TYPE,
            },
            "AWS.SNS.SMS.MaxPrice": {
                "DataType": "Number",
                "StringValue": str(settings.SNS_SMS_MAX_PRICE),
            },
        }

        # SenderID is only supported in certain countries and must be alphanumeric up to 11 chars
        if effective_sender_id and re.match(r"^[A-Za-z0-9]{1,11}$", effective_sender_id):
            attributes["AWS.SNS.SMS.SenderID"] = {
                "DataType": "String",
                "StringValue": effective_sender_id,
            }

        try:
            logger.info(f"Dispatching SMS via AWS SNS to {masked} (length: {len(message)} chars)")
            response = sns_client.publish(
                PhoneNumber=norm_phone,
                Message=message,
                MessageAttributes=attributes,
            )

            message_id = response.get("MessageId")
            logger.info(
                f"AWS SNS accepted SMS for {masked}. SNS MessageId: {message_id}"
            )
            # Crucial semantics: AWS SNS returns acceptance of the dispatch, NOT confirmed handset delivery.
            # Direct handset delivery feedback requires SNS topic subscription delivery status logs.
            return {
                "success": True,
                "status": "accepted",
                "message_id": message_id,
                "masked_phone": masked,
                "error": None,
                "is_transient": False,
            }

        except botocore.exceptions.NoCredentialsError:
            err_msg = "AWS SNS error: No AWS credentials found in environment or credential provider chain."
            logger.error(err_msg)
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "masked_phone": masked,
                "error": err_msg,
                "is_transient": False,
            }
        except botocore.exceptions.ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            msg = exc.response.get("Error", {}).get("Message", str(exc))
            err_msg = f"AWS SNS ClientError [{code}]: {msg}"
            is_transient = code in TRANSIENT_ERROR_CODES
            logger.error(f"Failed to dispatch SMS to {masked} (transient={is_transient}): {err_msg}")
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "masked_phone": masked,
                "error": err_msg,
                "is_transient": is_transient,
            }
        except Exception as exc:
            err_msg = f"Unexpected error during AWS SNS SMS dispatch: {type(exc).__name__}: {str(exc)}"
            # Network and timeout exceptions are transient
            exc_name = type(exc).__name__
            is_transient = "Timeout" in exc_name or "Connection" in exc_name
            logger.exception(f"Unexpected error dispatching SMS to {masked}: {err_msg}")
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "masked_phone": masked,
                "error": err_msg,
                "is_transient": is_transient,
            }

