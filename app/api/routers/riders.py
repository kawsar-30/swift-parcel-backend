from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import uuid
from pydantic import BaseModel
from app.database.database import get_db
from app.models.rider import Rider
from app.models.parcel import Parcel
from app.models.hub import Hub
from app.models.status_log import ParcelStatusLog
from app.models.user import User
from app.api.dependencies import require_role

router = APIRouter(prefix="/riders", tags=["Rider Management"])

class RiderStatusUpdate(BaseModel):
    is_available: bool

class RiderHubTransferRequest(BaseModel):
    new_hub_id: uuid.UUID
    note: str | None = "Transferred to next hub"

@router.get("")
async def get_all_riders(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    if current_user.role == "admin":
        query = select(Rider, User).join(User, Rider.user_id == User.id)
        result = await db.execute(query)
        riders = result.all()
        return [
            {
                "id": r.Rider.id,
                "name": r.User.name,
                "email": r.User.email,
                "phone": r.User.phone,
                "profile_picture": r.User.profile_picture,
                "hub_id": r.Rider.hub_id,
                "vehicle_type": r.Rider.vehicle_type,
                "is_available": r.Rider.is_available,
                "rider_type": r.Rider.rider_type,  # <-- Notun
            }
            for r in riders
        ]
    else:
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if not hub:
            return []
        query = (
            select(Rider, User)
            .join(User, Rider.user_id == User.id)
            .where(Rider.hub_id == hub.id)
        )
        result = await db.execute(query)
        riders = result.all()
        return [
            {
                "id": r.Rider.id,
                "name": r.User.name,
                "email": r.User.email,
                "phone": r.User.phone,
                "profile_picture": r.User.profile_picture,
                "hub_id": r.Rider.hub_id,
                "vehicle_type": r.Rider.vehicle_type,
                "is_available": r.Rider.is_available,
                "rider_type": r.Rider.rider_type,  # <-- Notun
            }
            for r in riders
        ]

@router.get("/by-hub/{hub_id}")
async def get_riders_by_hub(
    hub_id: uuid.UUID,
    rider_type: str | None = None,  # <-- Notun
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    query = (
        select(Rider, User)
        .join(User, Rider.user_id == User.id)
        .where(Rider.hub_id == hub_id)
    )
    
    if rider_type and rider_type != "both":
        # 'pickup' ba 'delivery' filter koro, kintu 'both' rider der o include koro
        query = query.where(Rider.rider_type.in_([rider_type, "both"]))
    
    result = await db.execute(query)
    riders = result.all()
    
    return [
        {
            "id": r.Rider.id,
            "name": r.User.name,
            "email": r.User.email,
            "phone": r.User.phone,
            "profile_picture": r.User.profile_picture,
            "hub_id": r.Rider.hub_id,
            "vehicle_type": r.Rider.vehicle_type,
            "is_available": r.Rider.is_available,
            "rider_type": r.Rider.rider_type,
        }
        for r in riders
    ]
@router.get("/tasks")
async def get_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    rider_res = await db.execute(select(Rider).where(Rider.user_id == current_user.id))
    rider = rider_res.scalar_one_or_none()
    if not rider:
        raise HTTPException(404, "Rider profile not found")

    query = select(Parcel).where(
        Parcel.assigned_rider_id == rider.id,
        Parcel.status.notin_(["CANCELLED"])
    )
    
    if rider.rider_type == "pickup":
        query = query.where(Parcel.status.in_(["PICKUP_ASSIGNED", "PICKED_UP", "AT_HUB", "DELIVERED"]))
    elif rider.rider_type == "delivery":
        query = query.where(Parcel.status.in_(["OUT_FOR_DELIVERY", "AT_HUB", "DELIVERED"]))
    
    query = query.order_by(Parcel.created_at.desc())
    result = await db.execute(query)
    parcels = result.scalars().all()
    
    response_data = []
    for p in parcels:
        response_data.append({
            "id": p.id,
            "tracking_id": p.tracking_id,
            "receiver_name": p.receiver_name,
            "receiver_phone": p.receiver_phone,
            "delivery_address": p.delivery_address,
            "delivery_city": p.delivery_city,
            "status": p.status,
            "cod_amount": p.cod_amount,
            "pickup_hub_id": p.pickup_hub_id,
            "delivery_hub_id": p.delivery_hub_id,
            "rider_type": rider.rider_type,
            "delivered_at": p.delivered_at,
        })
    
    return response_data
@router.patch("/me/availability")
async def toggle_availability(
    data: RiderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    rider_res = await db.execute(select(Rider).where(Rider.user_id == current_user.id))
    rider = rider_res.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(404, "Rider profile not found")
        
    rider.is_available = data.is_available
    await db.commit()
    
    return {
        "message": "Availability updated", 
        "is_available": rider.is_available
    }



@router.get("/me")
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    rider_res = await db.execute(select(Rider).where(Rider.user_id == current_user.id))
    rider = rider_res.scalar_one_or_none()
    if not rider:
        raise HTTPException(404, "Rider profile not found")

    return {
        "id": rider.id,
        "user_id": rider.user_id,
        "hub_id": rider.hub_id,
        "vehicle_type": rider.vehicle_type,
        "rider_type": rider.rider_type,
        "is_available": rider.is_available,
    }

@router.patch("/tasks/{parcel_id}/drop-at-hub")
async def drop_at_hub(
    parcel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    if not parcel:
        raise HTTPException(404, "Parcel not found")
        
    rider_res = await db.execute(select(Rider).where(Rider.user_id == current_user.id))
    rider = rider_res.scalar_one_or_none()
    if not rider or parcel.assigned_rider_id != rider.id:
        raise HTTPException(403, "This task is not assigned to you")

    if not rider.hub_id:
        raise HTTPException(400, "Rider is not assigned to any hub")
    
    hub_res = await db.execute(select(Hub).where(Hub.id == rider.hub_id))
    hub = hub_res.scalar_one_or_none()

    parcel.status = "AT_HUB"
    parcel.hub_id = hub.id
    parcel.assigned_rider_id = None  # Rider unassign koro
    
    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status="AT_HUB",
        note=f"Parcel dropped at {hub.name}",
        location=hub.name,
        updated_by=current_user.id
    )
    db.add(log)
    await db.commit()

    return {"message": f"Parcel dropped at {hub.name}", "parcel_id": parcel.id}

@router.patch("/tasks/{parcel_id}/transfer-hub")
async def rider_transfer_hub(
    parcel_id: uuid.UUID,
    data: RiderHubTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    if not parcel:
        raise HTTPException(404, "Parcel not found")
        
    hub_res = await db.execute(select(Hub).where(Hub.id == data.new_hub_id))
    hub = hub_res.scalar_one_or_none()
    if not hub:
        raise HTTPException(404, "Hub not found")

    parcel.hub_id = hub.id
    parcel.status = "IN_TRANSIT"
    
    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status="IN_TRANSIT",
        note=f"Parcel transferred to {hub.name}",
        location=hub.name,
        updated_by=current_user.id
    )
    db.add(log)
    await db.commit()
    return {"message": f"Parcel transferred to {hub.name}", "parcel_id": parcel.id}


@router.get("/{rider_id}/details")
async def get_rider_details(
    rider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    # Prothome rider_id diye try koro
    rider_res = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_res.scalar_one_or_none()
    
    # Jodi na pao, user_id diye try koro
    if not rider:
        rider_res = await db.execute(select(Rider).where(Rider.user_id == rider_id))
        rider = rider_res.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(404, "Rider not found")

    # User info
    user_res = await db.execute(select(User).where(User.id == rider.user_id))
    user = user_res.scalar_one_or_none()

    # Hub info
    hub_name = None
    hub_city = None
    if rider.hub_id:
        hub_res = await db.execute(select(Hub).where(Hub.id == rider.hub_id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            hub_name = hub.name
            hub_city = hub.city

    # Stats
    from sqlalchemy import func
    total_tasks = await db.scalar(select(func.count(Parcel.id)).where(Parcel.assigned_rider_id == rider.id))
    delivered_tasks = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & (Parcel.status == "DELIVERED")
    ))
    pending_tasks = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & (Parcel.status.in_(["PICKUP_ASSIGNED", "PICKED_UP", "OUT_FOR_DELIVERY"]))
    ))

    return {
        "id": rider.id,
        "user_id": rider.user_id,
        "name": user.name if user else "N/A",
        "email": user.email if user else "N/A",
        "phone": user.phone if user else None,
        "profile_picture": user.profile_picture if user else None,
        "nid_number": user.nid_number if user else None,
        "address": user.address if user else None,
        "hub_name": hub_name,
        "hub_city": hub_city,
        "vehicle_type": rider.vehicle_type,
        "rider_type": rider.rider_type,
        "is_available": rider.is_available,
        "total_tasks": total_tasks or 0,
        "delivered_tasks": delivered_tasks or 0,
        "pending_tasks": pending_tasks or 0,
    }



@router.get("/me/stats")
async def get_my_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("rider"))
):
    rider_res = await db.execute(select(Rider).where(Rider.user_id == current_user.id))
    rider = rider_res.scalar_one_or_none()
    if not rider:
        raise HTTPException(404, "Rider profile not found")

    from sqlalchemy import func
    from datetime import datetime, timedelta

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Total
    total_tasks = await db.scalar(select(func.count(Parcel.id)).where(Parcel.assigned_rider_id == rider.id))
    total_delivered = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & (Parcel.status == "DELIVERED")
    ))

    # Today
    today_picked = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & 
        (Parcel.status.in_(["PICKED_UP", "AT_HUB", "OUT_FOR_DELIVERY", "DELIVERED"])) &
        (Parcel.updated_at >= today_start)
    ))
    today_delivered = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & 
        (Parcel.status == "DELIVERED") &
        (Parcel.delivered_at >= today_start)
    ))

    # Week
    week_picked = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & 
        (Parcel.status.in_(["PICKED_UP", "AT_HUB", "OUT_FOR_DELIVERY", "DELIVERED"])) &
        (Parcel.updated_at >= week_start)
    ))
    week_delivered = await db.scalar(select(func.count(Parcel.id)).where(
        (Parcel.assigned_rider_id == rider.id) & 
        (Parcel.status == "DELIVERED") &
        (Parcel.delivered_at >= week_start)
    ))

    return {
        "total_tasks": total_tasks or 0,
        "total_delivered": total_delivered or 0,
        "today_picked": today_picked or 0,
        "today_delivered": today_delivered or 0,
        "week_picked": week_picked or 0,
        "week_delivered": week_delivered or 0,
    }