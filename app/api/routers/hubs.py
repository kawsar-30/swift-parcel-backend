from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database.database import get_db
from app.models.hub import Hub
from app.schemas.hub import HubCreate, HubResponse
from app.services.hub_service import create_hub
from app.api.dependencies import require_role
from app.models.user import User
from app.models.user import User
from app.models.rider import Rider
from app.models.parcel import Parcel
from sqlalchemy import func
from app.schemas.hub import HubDetailsResponse

router = APIRouter(prefix="/hubs", tags=["Hub Management"])

@router.post("", response_model=HubResponse, status_code=status.HTTP_201_CREATED)
async def add_hub(
    data: HubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    # Shudhu Admin hub create korte parbe
    hub = await create_hub(db, data)
    return hub

@router.get("", response_model=list[HubResponse])
async def get_all_hubs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager"))
):
    result = await db.execute(select(Hub).order_by(Hub.city.asc()))
    return result.scalars().all()

@router.delete("/{hub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hub(
    hub_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(Hub).where(Hub.id == hub_id))
    hub = result.scalar_one_or_none()
    if not hub:
        raise HTTPException(404, "Hub not found")
    
    await db.delete(hub)
    await db.commit()
    return None



# @router.get("/{hub_id}/details", response_model=HubDetailsResponse)
@router.get("/{hub_id}/details")
async def get_hub_details(
    hub_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager"))
):
    # Hub check
    hub_res = await db.execute(select(Hub).where(Hub.id == hub_id))
    hub = hub_res.scalar_one_or_none()
    if not hub:
        raise HTTPException(404, "Hub not found")

    # Manager details
    manager_name = None
    manager_phone = None
    if hub.manager_id:
        manager_res = await db.execute(select(User).where(User.id == hub.manager_id))
        manager = manager_res.scalar_one_or_none()
        if manager:
            manager_name = manager.name
            manager_phone = manager.phone

    # Riders list (with user details)
    riders_query = (
        select(Rider, User)
        .join(User, Rider.user_id == User.id)
        .where(Rider.hub_id == hub.id)
    )
    riders_result = await db.execute(riders_query)
    riders_data = riders_result.all()

    riders_list = [
        {
            "id": r.Rider.id,
            "name": r.User.name,
            "phone": r.User.phone,
            "vehicle_type": r.Rider.vehicle_type,
            "is_available": r.Rider.is_available,
        }
        for r in riders_data
    ]

    # Parcels stats
    total_parcels = await db.scalar(select(func.count(Parcel.id)).where(Parcel.hub_id == hub.id))
    pending_parcels = await db.scalar(select(func.count(Parcel.id)).where(Parcel.hub_id == hub.id, Parcel.status.in_(["PENDING", "AT_HUB", "PICKUP_ASSIGNED"])))
    delivered_parcels = await db.scalar(select(func.count(Parcel.id)).where(Parcel.hub_id == hub.id, Parcel.status == "DELIVERED"))

    return {
        "id": hub.id,
        "name": hub.name,
        "city": hub.city,
        "address": hub.address,
        "manager_name": manager_name,
        "manager_phone": manager_phone,
        "riders_count": len(riders_list),
        "riders": riders_list,  # <-- Notun add kora holo
        "total_parcels": total_parcels or 0,
        "pending_parcels": pending_parcels or 0,
        "delivered_parcels": delivered_parcels or 0,
    }