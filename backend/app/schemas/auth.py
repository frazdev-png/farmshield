import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Farmer's full name")
    email: EmailStr = Field(..., description="Unique contact email address")
    phone_number: str = Field(..., min_length=7, max_length=30, description="Contact phone number")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    
    # Optional farm creation fields provided during registration
    farm_name: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    acreage: Optional[str] = None
    total_area: Optional[float] = None
    area_unit: Optional[str] = "acres"
    primary_crops: Optional[str] = None
    soil_type: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("phone_number", mode="before")
    @classmethod
    def clean_phone_number(cls, v: str) -> str:
        if isinstance(v, str):
            # Strip extra whitespace while preserving standard international/local formatting
            cleaned = v.strip()
            # Verify contains at least some digits
            digits = re.sub(r"\D", "", cleaned)
            if len(digits) < 7:
                raise ValueError("Phone number must contain at least 7 digits.")
            return cleaned
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_full_name(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip()
            if len(cleaned) < 2:
                raise ValueError("Full name must be at least 2 characters long.")
            return cleaned
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone_number: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

