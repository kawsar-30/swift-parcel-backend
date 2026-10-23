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
from sqlalchemy import case

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
    # 1. Hub and Manager (Single Query)
    hub_query = (
        select(Hub, User.name.label("manager_name"), User.phone.label("manager_phone"))
        .outerjoin(User, Hub.manager_id == User.id)
        .where(Hub.id == hub_id)
    )
    hub_res = await db.execute(hub_query)
    hub_row = hub_res.first()
    if not hub_row:
        raise HTTPException(404, "Hub not found")
    
    hub = hub_row.Hub
    manager_name = hub_row.manager_name
    manager_phone = hub_row.manager_phone

    # 2. Riders List (Single Query)
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

    # 3. Parcels Stats (Single Query with aggregate)
    stats_query = select(
        func.count(Parcel.id).label("total"),
        func.sum(case((Parcel.status.in_(["PENDING", "AT_HUB", "PICKUP_ASSIGNED"]), 1), else_=0)).label("pending"),
        func.sum(case((Parcel.status == "DELIVERED", 1), else_=0)).label("delivered")
    ).where(Parcel.hub_id == hub.id)
    
    stats_res = await db.execute(stats_query)
    stats_row = stats_res.first()

    return {
        "id": hub.id,
        "name": hub.name,
        "city": hub.city,
        "address": hub.address,
        "manager_name": manager_name,
        "manager_phone": manager_phone,
        "riders_count": len(riders_list),
        "riders": riders_list,
        "total_parcels": stats_row.total or 0,
        "pending_parcels": stats_row.pending or 0,
        "delivered_parcels": stats_row.delivered or 0,
    }