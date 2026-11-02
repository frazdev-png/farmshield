import uuid
from typing import Callable, List, Optional, Union
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# Optional bearer scheme allows fallback to cookie if needed
security_bearer = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[str]:
    """
    Extract token from Authorization: Bearer <token> header or HttpOnly cookie.
    """
    if bearer and bearer.credentials:
        return bearer.credentials
    # Fallback to cookie
    return request.cookies.get("farmshield_access_token")


def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate JWT access token and return the authenticated User model.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id)
    user = db.scalar(stmt)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled.",
        )
    return current_user


def require_role(allowed_roles: Union[str, List[str]]) -> Callable[[User], User]:
    """
    Dependency factory that restricts route access to specific roles.
    Administrators possess supervisory access across farmer endpoints.
    """
    roles = [allowed_roles] if isinstance(allowed_roles, str) else allowed_roles

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == "admin" or current_user.role in roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: requires one of the following roles: {', '.join(roles)}.",
        )

    return role_checker


# Convenient role dependencies
require_admin = require_role("admin")
require_farmer = require_role("farmer")

