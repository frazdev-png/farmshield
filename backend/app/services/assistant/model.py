import logging
import os
from typing import Optional
import botocore.exceptions
from strands.models import BedrockModel
from app.core.config import settings

logger = logging.getLogger("farmshield.assistant.model")

_cached_bedrock_model: Optional[BedrockModel] = None


class BedrockConfigurationError(Exception):
    """Raised when Amazon Bedrock configuration or AWS credentials are not found."""
    pass


class BedrockInvocationError(Exception):
    """Raised when Amazon Bedrock invocation fails due to service error or throttling."""
    pass


def get_bedrock_model(force_refresh: bool = False) -> BedrockModel:
    """
    Returns a cached instance of BedrockModel configured with application settings.
    Does NOT reconnect or re-instantiate on every tool call.
    """
    global _cached_bedrock_model

    if _cached_bedrock_model is not None and not force_refresh:
        return _cached_bedrock_model

    model_id = settings.STRANDS_MODEL_ID or os.getenv("STRANDS_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    region_name = settings.AWS_REGION or os.getenv("AWS_REGION", "us-east-1")

    logger.info("Initializing BedrockModel: model_id=%s, region=%s", model_id, region_name)

    try:
        model = BedrockModel(
            model_id=model_id,
            region_name=region_name,
        )
        _cached_bedrock_model = model
        return model
    except Exception as exc:
        logger.error("Failed to initialize BedrockModel: %s", exc)
        raise BedrockConfigurationError(f"Bedrock initialization error: {str(exc)}") from exc

