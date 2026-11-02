from typing import List, Optional, Union
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "FarmShield AI Backend"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS origins can be provided as a JSON list string, comma-separated list, or list of strings
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://main.d3mw37v5rzxeqy.amplifyapp.com",
    ]

    # Database Configuration - PostgreSQL ready with SQLAlchemy 2.x
    DATABASE_URL: str = "sqlite:///./farmshield_dev.db"
    TEST_DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # JWT Authentication Configuration
    JWT_SECRET_KEY: str = "farmshield-insecure-dev-secret-key-change-in-production-32-chars-min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Strands AI & Amazon Bedrock Configuration
    STRANDS_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    AWS_REGION: str = "us-east-1"
    STRANDS_TIMEOUT_SECONDS: int = 30
    ALLOW_SIMULATED_AI: bool = True

    # AWS SNS SMS Notification System Configuration
    SNS_SMS_ENABLED: bool = True
    SNS_SMS_SIMULATE: bool = True
    SNS_SMS_SENDER_ID: Optional[str] = "FarmShield"
    SNS_SMS_MAX_PRICE: str = "0.05"  # Max price per message in USD
    SNS_SMS_TYPE: str = "Transactional"  # Transactional (high priority) or Promotional
    FARMSHIELD_DASHBOARD_URL: str = "http://localhost:5173"
    SNS_SMS_MAX_RETRIES: int = 3
    SNS_SMS_RETRY_BACKOFF_SECONDS: float = 1.0

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str) and v.startswith("sqlite:///./"):
            rel_file = v.replace("sqlite:///./", "")
            abs_path = (BACKEND_DIR / rel_file).as_posix()
            return f"sqlite:///{abs_path}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
