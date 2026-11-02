import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import require_farmer
from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.schemas.farm import (
    FarmCreate,
    FarmUpdate,
    FarmResponse,
    FarmCropCreate,
    FarmCropUpdate,
    FarmCropResponse,
)

router = APIRouter()


def convert_area(val: float, from_unit: str, to_unit: str) -> float:
    """Helper to convert area between acres and hectares."""
    if from_unit == to_unit:
        return val
    if from_unit == "hectares" and to_unit == "acres":
        return val * 2.47105381
    if from_unit == "acres" and to_unit == "hectares":
        return val / 2.47105381
    return val


def get_farmer_farm(farm_id: uuid.UUID, farmer_id: uuid.UUID, db: Session) -> Farm:
    """Enforces farm existence and strict ownership by the authenticated farmer."""
    farm = db.scalar(select(Farm).where(Farm.id == farm_id))
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found.",
        )
    if farm.farmer_id != farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this farm.",
        )
    return farm


def build_farm_response(farm: Farm) -> FarmResponse:
    crops = farm.crops or []
    total_cultivated = sum(
        convert_area(c.cultivated_area, c.area_unit, farm.area_unit) for c in crops
    )
    return FarmResponse(
        id=farm.id,
        farmer_id=farm.farmer_id,
        farm_name=farm.farm_name,
        district=farm.district,
        village=farm.village,
        address=farm.address,
        latitude=farm.latitude,
        longitude=farm.longitude,
        total_area=farm.total_area,
        area_unit=farm.area_unit,
        soil_type=farm.soil_type,
        created_at=farm.created_at,
        updated_at=farm.updated_at,
        crops_count=len(crops),
        total_cultivated_area=round(total_cultivated, 2),
        crops=[FarmCropResponse.model_validate(c) for c in crops],
    )


# ==========================================
# FARM ENDPOINTS
# ==========================================

@router.post(
    "",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new farm",
)
def create_farm(
    payload: FarmCreate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Registers a new farm owned by the authenticated farmer."""
    farm = Farm(
        farmer_id=current_user.id,
        farm_name=payload.farm_name,
        district=payload.district,
        village=payload.village,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        total_area=payload.total_area,
        area_unit=payload.area_unit,
        soil_type=payload.soil_type,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return build_farm_response(farm)


@router.get(
    "",
    response_model=List[FarmResponse],
    summary="List all farms for current farmer",
)
def list_farms(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Retrieves all farms owned exclusively by the authenticated farmer."""
    stmt = (
        select(Farm)
        .where(Farm.farmer_id == current_user.id)
        .order_by(Farm.created_at.desc())
    )
    farms = db.scalars(stmt).all()
    return [build_farm_response(f) for f in farms]


@router.get(
    "/{farm_id}",
    response_model=FarmResponse,
    summary="Get farm details by ID",
)
def get_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Retrieves details of a specific farm owned by the authenticated farmer."""
    farm = get_farmer_farm(farm_id, current_user.id, db)
    return build_farm_response(farm)


@router.put(
    "/{farm_id}",
    response_model=FarmResponse,
    summary="Update farm details",
)
def update_farm(
    farm_id: uuid.UUID,
    payload: FarmUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Updates property fields of a farm. Enforces that total area cannot be reduced below current crops."""
    farm = get_farmer_farm(farm_id, current_user.id, db)

    target_unit = payload.area_unit if payload.area_unit is not None else farm.area_unit
    target_area = payload.total_area if payload.total_area is not None else farm.total_area

    # Check that new total area accommodates current crops
    if farm.crops:
        current_crops_area = sum(
            convert_area(c.cultivated_area, c.area_unit, target_unit) for c in farm.crops
        )
        if current_crops_area > target_area + 0.001:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total farm area ({target_area} {target_unit}) cannot be smaller than currently cultivated crops ({round(current_crops_area, 2)} {target_unit}).",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(farm, field, value)

    db.commit()
    db.refresh(farm)
    return build_farm_response(farm)


@router.delete(
    "/{farm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete farm and associated crops",
)
def delete_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Deletes the farm and cascades deletion to all associated crops."""
    farm = get_farmer_farm(farm_id, current_user.id, db)
    db.delete(farm)
    db.commit()
    return None


# ==========================================
# CROP ENDPOINTS
# ==========================================

@router.post(
    "/{farm_id}/crops",
    response_model=FarmCropResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a crop to a farm",
)
def create_farm_crop(
    farm_id: uuid.UUID,
    payload: FarmCropCreate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Adds a cultivated crop plot to an authenticated farmer's farm."""
    farm = get_farmer_farm(farm_id, current_user.id, db)

    # 1. Single crop area must not exceed farm total area
    new_crop_area_in_farm_unit = convert_area(
        payload.cultivated_area, payload.area_unit, farm.area_unit
    )
    if new_crop_area_in_farm_unit > farm.total_area:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crop cultivated area ({payload.cultivated_area} {payload.area_unit}) exceeds farm total area ({farm.total_area} {farm.area_unit}).",
        )

    # 2. Cumulative cultivated area check
    existing_crops_area = sum(
        convert_area(c.cultivated_area, c.area_unit, farm.area_unit) for c in farm.crops
    )
    if existing_crops_area + new_crop_area_in_farm_unit > farm.total_area + 0.001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adding this crop ({payload.cultivated_area} {payload.area_unit}) would cause total cultivated area ({round(existing_crops_area + new_crop_area_in_farm_unit, 2)} {farm.area_unit}) to exceed the farm's total area ({farm.total_area} {farm.area_unit}).",
        )

    crop = FarmCrop(
        farm_id=farm.id,
        crop_name=payload.crop_name,
        variety=payload.variety,
        cultivated_area=payload.cultivated_area,
        area_unit=payload.area_unit,
        sowing_date=payload.sowing_date,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.get(
    "/{farm_id}/crops",
    response_model=List[FarmCropResponse],
    summary="List all crops for a farm",
)
def list_farm_crops(
    farm_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Lists all crops cultivated on the specified farm."""
    farm = get_farmer_farm(farm_id, current_user.id, db)
    stmt = (
        select(FarmCrop)
        .where(FarmCrop.farm_id == farm.id)
        .order_by(FarmCrop.created_at.desc())
    )
    crops = db.scalars(stmt).all()
    return crops


@router.put(
    "/{farm_id}/crops/{crop_id}",
    response_model=FarmCropResponse,
    summary="Update crop information",
)
def update_farm_crop(
    farm_id: uuid.UUID,
    crop_id: uuid.UUID,
    payload: FarmCropUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Updates an existing crop on a farm."""
    farm = get_farmer_farm(farm_id, current_user.id, db)
    crop = db.scalar(
        select(FarmCrop).where(FarmCrop.id == crop_id, FarmCrop.farm_id == farm.id)
    )
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop not found on this farm.",
        )

    target_crop_unit = payload.area_unit if payload.area_unit is not None else crop.area_unit
    target_crop_area = payload.cultivated_area if payload.cultivated_area is not None else crop.cultivated_area

    # Validate against farm total area
    new_crop_area_in_farm_unit = convert_area(target_crop_area, target_crop_unit, farm.area_unit)
    if new_crop_area_in_farm_unit > farm.total_area:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crop cultivated area ({target_crop_area} {target_crop_unit}) exceeds farm total area ({farm.total_area} {farm.area_unit}).",
        )

    # Cumulative check excluding this crop's old area
    other_crops_area = sum(
        convert_area(c.cultivated_area, c.area_unit, farm.area_unit)
        for c in farm.crops
        if c.id != crop.id
    )
    if other_crops_area + new_crop_area_in_farm_unit > farm.total_area + 0.001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Updated crop area would cause total cultivated area to exceed farm total area ({farm.total_area} {farm.area_unit}).",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(crop, field, value)

    db.commit()
    db.refresh(crop)
    return crop


@router.delete(
    "/{farm_id}/crops/{crop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a crop from a farm",
)
def delete_farm_crop(
    farm_id: uuid.UUID,
    crop_id: uuid.UUID,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Deletes a crop plot from the farm."""
    farm = get_farmer_farm(farm_id, current_user.id, db)
    crop = db.scalar(
        select(FarmCrop).where(FarmCrop.id == crop_id, FarmCrop.farm_id == farm.id)
    )
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop not found on this farm.",
        )
    db.delete(crop)
    db.commit()
    return None

