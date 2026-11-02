from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new farmer account",
    description="Registers a new agricultural producer. Role is strictly assigned as 'farmer'.",
)
def register_farmer(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    # Check for duplicate email
    existing_email = db.scalar(select(User).where(User.email == payload.email))
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Check for duplicate phone number
    existing_phone = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this phone number already exists.",
        )

    # Strict security: Public registration can NEVER provision admin accounts
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        role="farmer",
        is_active=True,
    )

    db.add(user)
    db.flush()

    # If farmer provided farm details during registration, create their initial real farm
    if payload.farm_name and payload.farm_name.strip():
        # Parse total area
        total_area = 10.0
        if payload.total_area is not None and payload.total_area > 0:
            total_area = float(payload.total_area)
        elif payload.acreage:
            try:
                # Extract first numeric float
                m = re.search(r"(\d+(\.\d+)?)", str(payload.acreage))
                if m:
                    total_area = float(m.group(1))
            except Exception:
                pass

        lat = payload.latitude if payload.latitude is not None else 31.5204
        lon = payload.longitude if payload.longitude is not None else 74.3587
        district = payload.district or payload.region or "Central Punjab"
        village = payload.village or "Village 1"

        farm = Farm(
            farmer_id=user.id,
            farm_name=payload.farm_name.strip(),
            district=district.strip(),
            village=village.strip(),
            latitude=round(float(lat), 4),
            longitude=round(float(lon), 4),
            total_area=round(float(total_area), 2),
            area_unit=payload.area_unit or "acres",
            soil_type=payload.soil_type or "Loam",
        )
        db.add(farm)
        db.flush()

        # If primary crops were specified, register the primary crop
        if payload.primary_crops and payload.primary_crops.strip():
            crop_names = [c.strip() for c in payload.primary_crops.split(",") if c.strip()]
            for crop_name in crop_names[:3]:  # up to 3 initial crops
                crop = FarmCrop(
                    farm_id=farm.id,
                    crop_name=crop_name,
                    cultivated_area=round(float(total_area / max(1, len(crop_names[:3]))), 2),
                    area_unit=farm.area_unit,
                )
                db.add(crop)

    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT token",
    description="Authenticates credentials and returns a signed bearer token. Sets HttpOnly cookie when applicable.",
)
def login(
    payload: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    # Lookup by normalized email or phone number
    user = db.scalar(
        select(User).where(
            (User.email == payload.email) | (User.phone_number == payload.email)
        )
    )

    # Generic error message to prevent account enumeration
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify account active status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled.",
        )

    # Issue signed JWT token
    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        email=user.email,
    )

    # Set secure HttpOnly cookie for defense-in-depth against XSS
    is_prod = settings.APP_ENV.lower() == "production"
    response.set_cookie(
        key="farmshield_access_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
    description="Returns the authenticated user details for the active JWT session.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    return current_user

