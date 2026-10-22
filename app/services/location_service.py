from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rider_location import RiderLocation
from app.models.rider import Rider
from app.schemas.rider_location import LocationUpdate
from fastapi import HTTPException
import uuid

async def update_rider_location(db: AsyncSession, user_id: uuid.UUID, data: LocationUpdate):
    # Rider profile khuje ber koro
    rider_res = await db.execute(select(Rider).where(Rider.user_id == user_id))
    rider = rider_res.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider profile not found")

    # Jodi age location theke thake, update koro, na thakle create koro
    loc_res = await db.execute(select(RiderLocation).where(RiderLocation.rider_id == rider.id))
    location = loc_res.scalar_one_or_none()

    if location:
        location.latitude = data.latitude
        location.longitude = data.longitude
        location.parcel_id = data.parcel_id
    else:
        location = RiderLocation(
            rider_id=rider.id,
            latitude=data.latitude,
            longitude=data.longitude,
            parcel_id=data.parcel_id
        )
        db.add(location)

    await db.commit()
    await db.refresh(location)
    return location

async def get_parcel_location(db: AsyncSession, parcel_id: uuid.UUID):
    # Parcel er assigned rider khuje ber koro
    from app.models.parcel import Parcel
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    
    if not parcel or not parcel.assigned_rider_id:
        raise HTTPException(status_code=404, detail="No rider assigned to this parcel")

    loc_res = await db.execute(select(RiderLocation).where(RiderLocation.rider_id == parcel.assigned_rider_id))
    location = loc_res.scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not updated yet")

    return {
        "rider_id": location.rider_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "updated_at": location.updated_at
    }