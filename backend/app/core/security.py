from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import argon2
from argon2.exceptions import VerifyMismatchError, InvalidHashError
import jwt
from app.core.config import settings

# Argon2 PasswordHasher with OWASP recommended configuration
_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain text password against Argon2 hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(
    subject: str,
    role: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create signed JWT access token with user claims and expiration."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate signed JWT token.
    Raises jwt.PyJWTError if invalid or expired.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

