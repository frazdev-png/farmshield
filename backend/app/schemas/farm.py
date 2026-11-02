import uuid
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FarmBase(BaseModel):
    farm_name: str = Field(..., min_length=2, max_length=255, description="Name or identifier of the farm")
    district: str = Field(..., min_length=1, max_length=100, description="District or county")
    village: str = Field(..., min_length=1, max_length=100, description="Village, town, or sub-locality")
    address: Optional[str] = Field(None, max_length=255, description="Street address or landmark description")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180")
    total_area: float = Field(..., gt=0.0, description="Total land area (must be greater than 0)")
    area_unit: str = Field("acres", pattern="^(acres|hectares)$", description="Unit of measurement: acres or hectares")
    soil_type: Optional[str] = Field(None, max_length=100, description="Dominant soil classification")

    @field_validator("farm_name", "district", "village", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Field cannot be empty or purely whitespace.")
            return cleaned
        return v

    @field_validator("area_unit")
    @classmethod
    def validate_area_unit(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("acres", "hectares"):
            raise ValueError("Area unit must be either 'acres' or 'hectares'.")
        return v_clean


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    farm_name: Optional[str] = Field(None, min_length=2, max_length=255)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    village: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    total_area: Optional[float] = Field(None, gt=0.0)
    area_unit: Optional[str] = Field(None, pattern="^(acres|hectares)$")
    soil_type: Optional[str] = Field(None, max_length=100)

    @field_validator("farm_name", "district", "village", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Field cannot be empty or purely whitespace.")
            return cleaned
        return v

    @field_validator("area_unit")
    @classmethod
    def validate_area_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip().lower()
            if v_clean not in ("acres", "hectares"):
                raise ValueError("Area unit must be either 'acres' or 'hectares'.")
            return v_clean
        return v


class FarmCropBase(BaseModel):
    crop_name: str = Field(..., min_length=1, max_length=100, description="Crop name (e.g., Maize, Wheat)")
    variety: Optional[str] = Field(None, max_length=100, description="Specific seed variety or cultivar")
    cultivated_area: float = Field(..., gt=0.0, description="Area under cultivation for this crop (must be > 0)")
    area_unit: str = Field("acres", pattern="^(acres|hectares)$", description="Unit of measurement: acres or hectares")
    sowing_date: Optional[date] = Field(None, description="Date when crop was sown/planted (YYYY-MM-DD)")

    @field_validator("crop_name", mode="before")
    @classmethod
    def strip_crop_name(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Crop name cannot be empty.")
            return cleaned
        return v

    @field_validator("area_unit")
    @classmethod
    def validate_crop_area_unit(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("acres", "hectares"):
            raise ValueError("Area unit must be either 'acres' or 'hectares'.")
        return v_clean


class FarmCropCreate(FarmCropBase):
    pass


class FarmCropUpdate(BaseModel):
    crop_name: Optional[str] = Field(None, min_length=1, max_length=100)
    variety: Optional[str] = Field(None, max_length=100)
    cultivated_area: Optional[float] = Field(None, gt=0.0)
    area_unit: Optional[str] = Field(None, pattern="^(acres|hectares)$")
    sowing_date: Optional[date] = None

    @field_validator("crop_name", mode="before")
    @classmethod
    def strip_crop_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Crop name cannot be empty.")
            return cleaned
        return v

    @field_validator("area_unit")
    @classmethod
    def validate_crop_area_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip().lower()
            if v_clean not in ("acres", "hectares"):
                raise ValueError("Area unit must be either 'acres' or 'hectares'.")
            return v_clean
        return v


class FarmCropResponse(FarmCropBase):
    id: uuid.UUID
    farm_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FarmResponse(FarmBase):
    id: uuid.UUID
    farmer_id: uuid.UUID
    crops_count: int = 0
    total_cultivated_area: float = 0.0
    crops: List[FarmCropResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

