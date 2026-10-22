from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database.database import get_db
from app.api.dependencies import require_role
from app.schemas.rider_location import LocationUpdate, LocationResponse
from app.services.location_service import update_rider_location, get_parcel_location

router = APIRouter(prefix="/locations", tags=["Live Locations"])

@router.patch("/update", response_model=LocationResponse)
async def update_location(
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    # Rider nijer location update korbe
    location = await update_rider_location(db, current_user.id, data)
    return location

@router.get("/parcel/{parcel_id}")
async def track_parcel_location(
    parcel_id: UUID,
    db: AsyncSession = Depends(get_db)
    # Public route, kono token lagbe na
):
    return await get_parcel_location(db, parcel_id)