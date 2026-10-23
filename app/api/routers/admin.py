from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from app.database.database import get_db
from app.models.parcel import Parcel
from app.models.rider import Rider
from app.models.user import User
from app.models.hub import Hub
from app.models.zone import Zone
from app.models.payment import Payment
from app.models.status_log import ParcelStatusLog
from app.models.pricing_rule import PricingRule
from app.api.dependencies import require_role
from app.utils.parcel_rules import validate_status_transition
from app.schemas.auth import InternalUserCreate, UserResponse, UserUpdate
from app.schemas.pricing import PricingRuleCreate, PricingRuleResponse
from app.services.user_service import create_internal_user
from app.services.notification_service import create_notification

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

class AssignRiderRequest(BaseModel):
    rider_id: uuid.UUID

class UpdateStatusRequest(BaseModel):
    status: str
    note: str | None = None
    location: str | None = None

class HubTransferRequest(BaseModel):
    new_hub_id: uuid.UUID
    note: Optional[str] = "Parcel transferred to new hub"

# --- Parcel APIs ---

@router.get("/parcels")
async def get_all_parcels(
    skip: int = 0,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    query = select(Parcel).options(selectinload(Parcel.items)).order_by(Parcel.created_at.desc())
    
    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                ((Parcel.pickup_hub_id == hub.id) & 
                 (Parcel.status.in_(["PENDING", "PICKUP_ASSIGNED", "PICKED_UP", "AT_HUB"]))) |
                ((Parcel.delivery_hub_id == hub.id) & 
                 (Parcel.status.in_(["IN_TRANSIT", "AT_HUB", "OUT_FOR_DELIVERY", "DELIVERED"]))) |
                (Parcel.status.like(f"RECEIVED_AT_%"))
            )
        else:
            return {"data": [], "total": 0, "skip": skip, "limit": limit}

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    parcels = result.scalars().all()

    if not parcels:
        return {"data": [], "total": 0, "skip": skip, "limit": limit}

    zone_ids = {p.pickup_zone_id for p in parcels if p.pickup_zone_id} | {p.delivery_zone_id for p in parcels if p.delivery_zone_id}
    hub_ids = {p.pickup_hub_id for p in parcels if p.pickup_hub_id} | {p.delivery_hub_id for p in parcels if p.delivery_hub_id}
    rider_ids = {p.assigned_rider_id for p in parcels if p.assigned_rider_id}
    parcel_ids = [p.id for p in parcels]

    zones_map = {}
    if zone_ids:
        z_res = await db.execute(select(Zone.id, Zone.name).where(Zone.id.in_(zone_ids)))
        zones_map = {row.id: row.name for row in z_res.all()}

    hubs_map = {}
    if hub_ids:
        h_res = await db.execute(select(Hub.id, Hub.name).where(Hub.id.in_(hub_ids)))
        hubs_map = {row.id: row.name for row in h_res.all()}

    riders_map = {}
    if rider_ids:
        r_res = await db.execute(
            select(Rider.id, User.name)
            .join(User, Rider.user_id == User.id)
            .where(Rider.id.in_(rider_ids))
        )
        riders_map = {row.id: row.name for row in r_res.all()}

    payments_map = {}
    if parcel_ids:
        p_res = await db.execute(
            select(Payment.parcel_id, Payment.status)
            .where(Payment.parcel_id.in_(parcel_ids))
            .order_by(Payment.created_at.desc())
        )
        for p_id, p_status in p_res.all():
            if p_id not in payments_map:
                payments_map[p_id] = p_status

    response_data = []
    for p in parcels:
        response_data.append({
            "id": p.id,
            "tracking_id": p.tracking_id,
            "sender_name": p.sender_name,
            "sender_phone": p.sender_phone,
            "pickup_address": p.pickup_address,
            "receiver_name": p.receiver_name,
            "receiver_phone": p.receiver_phone,
            "delivery_address": p.delivery_address,
            "delivery_city": p.delivery_city,
            "weight_kg": p.weight_kg,
            "parcel_type": p.parcel_type,
            "delivery_type": p.delivery_type,
            "cod_amount": p.cod_amount,
            "delivery_charge": p.delivery_charge,
            "total_amount": p.total_amount,
            "status": p.status,
            "created_at": p.created_at,
            "assigned_rider_id": p.assigned_rider_id,
            "assigned_rider_name": riders_map.get(p.assigned_rider_id),
            "hub_id": p.hub_id,
            "pickup_hub_id": p.pickup_hub_id,
            "delivery_hub_id": p.delivery_hub_id,
            "payment_status": payments_map.get(p.id),
            "items": [
                {
                    "id": item.id,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                } for item in p.items
            ] if p.items else [],
            "pickup_zone_name": zones_map.get(p.pickup_zone_id),
            "delivery_zone_name": zones_map.get(p.delivery_zone_id),
            "pickup_hub_name": hubs_map.get(p.pickup_hub_id),
            "delivery_hub_name": hubs_map.get(p.delivery_hub_id),
        })

    return {
        "data": response_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.patch("/parcels/{parcel_id}/assign-rider")
async def assign_rider(
    parcel_id: uuid.UUID,
    data: AssignRiderRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    if not parcel:
        raise HTTPException(404, "Parcel not found")
        
    rider_res = await db.execute(select(Rider).where(Rider.id == data.rider_id))
    rider = rider_res.scalar_one_or_none()
    if not rider:
        raise HTTPException(404, "Rider not found")

    parcel.assigned_rider_id = rider.id
    
    if parcel.status in ["PENDING", "AT_HUB"]:
        parcel.status = "PICKUP_ASSIGNED"
        log = ParcelStatusLog(
            parcel_id=parcel.id, 
            status="PICKUP_ASSIGNED", 
            note="Rider assigned by admin",
            updated_by=current_user.id
        )
        db.add(log)

    await db.commit()
    return {"message": "Rider assigned successfully", "status": parcel.status}

@router.patch("/parcels/{parcel_id}/status")
async def update_parcel_status(
    parcel_id: uuid.UUID,
    data: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager", "rider"))
):
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    if not parcel:
        raise HTTPException(404, "Parcel not found")

    validate_status_transition(parcel.status, data.status)
    
    if data.status.startswith("RECEIVED_AT_"):
        if data.location:
            hub_res = await db.execute(select(Hub).where(Hub.name == data.location))
            hub = hub_res.scalar_one_or_none()
            if hub:
                parcel.hub_id = hub.id

    if data.status == "DELIVERED":
        parcel.delivered_at = datetime.utcnow()

    parcel.status = data.status

    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status=data.status,
        note=data.note,
        location=data.location,
        updated_by=current_user.id
    )
    db.add(log)
    
    await create_notification(
        db, 
        parcel.sender_id, 
        f"Parcel {data.status.replace('_', ' ').title()}",
        f"Your parcel {parcel.tracking_id} is now {data.status}."
    )
    
    await db.commit()
    return {"message": f"Status updated to {data.status}", "parcel_id": parcel.id}

@router.patch("/parcels/{parcel_id}/transfer-hub")
async def transfer_parcel_hub(
    parcel_id: uuid.UUID,
    data: HubTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
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
    parcel.assigned_rider_id = None
    if parcel.status in ["AT_HUB", "PICKED_UP"]:
        parcel.status = "IN_TRANSIT"
    
    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status=parcel.status,
        note=data.note,
        location=hub.name,
        updated_by=current_user.id
    )
    db.add(log)

    await db.commit()
    return {"message": f"Parcel transferred to {hub.name}", "parcel_id": parcel.id}

# --- Internal User Management APIs ---

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    data: InternalUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    user = await create_internal_user(db, data)
    return user

@router.get("/users")
async def get_all_users(
    role: str | None = Query(None, description="Filter by role"),
    hub_id: str | None = Query(None, description="Filter by hub"),
    skip: int = 0,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager"))
):
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if current_user.role == "admin" and hub_id:
        if role == "manager":
            query = query.where(
                User.id.in_(
                    select(Hub.manager_id).where(Hub.id == uuid.UUID(hub_id)).where(Hub.manager_id.isnot(None))
                )
            )
        elif role == "rider":
            query = query.where(
                User.id.in_(
                    select(Rider.user_id).where(Rider.hub_id == uuid.UUID(hub_id))
                )
            )
    
    if current_user.role == "manager" and role == "rider":
        hub_rider_subquery = (
            select(Rider.user_id)
            .join(Hub, Hub.id == Rider.hub_id)
            .where(Hub.manager_id == current_user.id)
        )
        query = query.where(User.id.in_(hub_rider_subquery))
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {"data": users, "total": total}

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if data.name is not None: user.name = data.name
    if data.phone is not None: user.phone = data.phone
    if data.profile_picture is not None: user.profile_picture = data.profile_picture
    if data.nid_number is not None: user.nid_number = data.nid_number
    if data.address is not None: user.address = data.address
    
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
        
    rider_res = await db.execute(select(Rider).where(Rider.user_id == user_id))
    rider = rider_res.scalar_one_or_none()
    if rider:
        await db.delete(rider)

    await db.delete(user)
    await db.commit()
    return None

@router.get("/managers/{manager_id}/details")
async def get_manager_details(
    manager_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    manager_res = await db.execute(select(User).where(User.id == manager_id, User.role == "manager"))
    manager = manager_res.scalar_one_or_none()
    if not manager:
        raise HTTPException(404, "Manager not found")

    hub_res = await db.execute(select(Hub).where(Hub.manager_id == manager.id))
    hub = hub_res.scalar_one_or_none()

    riders_count = 0
    total_parcels = 0
    delivered_parcels = 0
    pending_parcels = 0

    if hub:
        riders_count = await db.scalar(select(func.count(Rider.id)).where(Rider.hub_id == hub.id))
        total_parcels = await db.scalar(select(func.count(Parcel.id)).where(
            (Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)
        ))
        delivered_parcels = await db.scalar(select(func.count(Parcel.id)).where(
            ((Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)) & 
            (Parcel.status == "DELIVERED")
        ))
        pending_parcels = await db.scalar(select(func.count(Parcel.id)).where(
            ((Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)) & 
            (Parcel.status.in_(["PENDING", "PICKUP_ASSIGNED", "AT_HUB"]))
        ))

    return {
        "id": manager.id,
        "name": manager.name,
        "email": manager.email,
        "phone": manager.phone,
        "profile_picture": manager.profile_picture,
        "nid_number": manager.nid_number,
        "address": manager.address,
        "hub_name": hub.name if hub else None,
        "hub_city": hub.city if hub else None,
        "hub_address": hub.address if hub else None,
        "riders_count": riders_count or 0,
        "total_parcels": total_parcels or 0,
        "delivered_parcels": delivered_parcels or 0,
        "pending_parcels": pending_parcels or 0,
    }

# --- Pricing Rules APIs ---

@router.post("/pricing-rules", response_model=PricingRuleResponse, status_code=201)
async def create_pricing_rule(
    data: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    new_rule = PricingRule(**data.model_dump())
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    f_hub = await db.execute(select(Hub).where(Hub.id == new_rule.from_hub_id))
    t_hub = await db.execute(select(Hub).where(Hub.id == new_rule.to_hub_id))
    from_hub = f_hub.scalar_one_or_none()
    to_hub = t_hub.scalar_one_or_none()

    return {
        "id": new_rule.id,
        "from_hub_id": new_rule.from_hub_id,
        "to_hub_id": new_rule.to_hub_id,
        "base_price": new_rule.base_price,
        "per_kg_price": new_rule.per_kg_price,
        "express_multiplier": new_rule.express_multiplier,
        "from_hub_name": from_hub.name if from_hub else None,
        "to_hub_name": to_hub.name if to_hub else None,
    }

@router.get("/pricing-rules", response_model=list[PricingRuleResponse])
async def get_pricing_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(PricingRule))
    rules = result.scalars().all()
    
    response_data = []
    for rule in rules:
        f_hub = await db.execute(select(Hub).where(Hub.id == rule.from_hub_id))
        t_hub = await db.execute(select(Hub).where(Hub.id == rule.to_hub_id))
        from_hub = f_hub.scalar_one_or_none()
        to_hub = t_hub.scalar_one_or_none()
        
        response_data.append({
            "id": rule.id,
            "from_hub_id": rule.from_hub_id,
            "to_hub_id": rule.to_hub_id,
            "base_price": rule.base_price,
            "per_kg_price": rule.per_kg_price,
            "express_multiplier": rule.express_multiplier,
            "from_hub_name": from_hub.name if from_hub else None,
            "to_hub_name": to_hub.name if to_hub else None,
        })
        
    return response_data

@router.put("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    rule_id: uuid.UUID,
    data: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Pricing rule not found")

    rule.from_hub_id = data.from_hub_id
    rule.to_hub_id = data.to_hub_id
    rule.base_price = data.base_price
    rule.per_kg_price = data.per_kg_price
    rule.express_multiplier = data.express_multiplier

    await db.commit()
    await db.refresh(rule)
    
    f_hub = await db.execute(select(Hub).where(Hub.id == rule.from_hub_id))
    t_hub = await db.execute(select(Hub).where(Hub.id == rule.to_hub_id))
    from_hub = f_hub.scalar_one_or_none()
    to_hub = t_hub.scalar_one_or_none()

    return {
        "id": rule.id,
        "from_hub_id": rule.from_hub_id,
        "to_hub_id": rule.to_hub_id,
        "base_price": rule.base_price,
        "per_kg_price": rule.per_kg_price,
        "express_multiplier": rule.express_multiplier,
        "from_hub_name": from_hub.name if from_hub else None,
        "to_hub_name": to_hub.name if to_hub else None,
    }

@router.delete("/pricing-rules/{rule_id}", status_code=204)
async def delete_pricing_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Pricing rule not found")

    await db.delete(rule)
    await db.commit()
    return None

# --- Dashboard Stats API ---

@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    query = select(Parcel)
    
    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                ((Parcel.pickup_hub_id == hub.id) & (Parcel.status.in_(["PENDING", "PICKUP_ASSIGNED", "PICKED_UP"]))) |
                ((Parcel.delivery_hub_id == hub.id) & (Parcel.status.in_(["IN_TRANSIT", "AT_HUB", "RECEIVED_AT_DHAKA_CENTRAL_HUB", "OUT_FOR_DELIVERY"])))
            )

    total_parcels = await db.scalar(select(func.count()).select_from(query.subquery()))
    delivered = await db.scalar(select(func.count()).select_from(query.where(Parcel.status == "DELIVERED").subquery()))
    pending = await db.scalar(select(func.count()).select_from(query.where(Parcel.status.in_(["PENDING", "PICKUP_ASSIGNED", "AT_HUB"])).subquery()))
    
    revenue = await db.scalar(select(func.sum(Parcel.total_amount)).select_from(query.where(Parcel.status == "DELIVERED").subquery()))
    
    return {
        "total_parcels": total_parcels or 0,
        "delivered": delivered or 0,
        "pending": pending or 0,
        "total_revenue": revenue or 0
    }

# --- Combined Dashboard Stats API (নতুন ও সবচেয়ে গুরুত্বপূর্ণ) ---
@router.get("/dashboard-stats")
async def get_dashboard_combined_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    hub_id = None
    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            hub_id = hub.id
        else:
            return {"stats": {}, "daily_volume": [], "daily_revenue": [], "success_rate": {}, "top_cities": []}

    # 1. Base Stats
    stats_query = select(
        func.count(Parcel.id).label("total"),
        func.sum(case((Parcel.status == "DELIVERED", 1), else_=0)).label("delivered"),
        func.sum(case((Parcel.status.in_(["PENDING", "PICKUP_ASSIGNED", "AT_HUB"]), 1), else_=0)).label("pending"),
        func.sum(case((Parcel.status == "DELIVERED", Parcel.total_amount), else_=0)).label("revenue")
    )
    if hub_id:
        stats_query = stats_query.where(
            (Parcel.pickup_hub_id == hub_id) | (Parcel.delivery_hub_id == hub_id)
        )
    stats_res = await db.execute(stats_query)
    stats_row = stats_res.first()

    # 2. Daily Volume
    vol_query = select(
        func.date(Parcel.created_at).label("date"),
        func.count(Parcel.id).label("count")
    ).where(Parcel.created_at >= start_date, Parcel.created_at < end_date)
    if hub_id:
        vol_query = vol_query.where((Parcel.pickup_hub_id == hub_id) | (Parcel.delivery_hub_id == hub_id))
    vol_query = vol_query.group_by(func.date(Parcel.created_at)).order_by(func.date(Parcel.created_at).asc())
    vol_res = await db.execute(vol_query)
    daily_volume = [{"date": str(row.date), "count": row.count} for row in vol_res.all()]

    # 3. Daily Revenue
    rev_query = select(
        func.date(Parcel.created_at).label("date"),
        func.sum(Parcel.total_amount).label("revenue")
    ).where(Parcel.created_at >= start_date, Parcel.created_at < end_date)
    if hub_id:
        rev_query = rev_query.where((Parcel.pickup_hub_id == hub_id) | (Parcel.delivery_hub_id == hub_id))
    rev_query = rev_query.group_by(func.date(Parcel.created_at)).order_by(func.date(Parcel.created_at).asc())
    rev_res = await db.execute(rev_query)
    daily_revenue = [{"date": str(row.date), "revenue": float(row.revenue or 0)} for row in rev_res.all()]

    # 4. Success Rate
    total = stats_row.total or 0
    delivered = stats_row.delivered or 0
    success_rate = {
        "total_parcels": total,
        "delivered_parcels": delivered,
        "success_rate": round((delivered / total * 100), 2) if total > 0 else 0.0
    }

    # 5. Top Cities
    city_query = select(
        Parcel.delivery_city.label("city"),
        func.count(Parcel.id).label("count")
    )
    if hub_id:
        city_query = city_query.where((Parcel.pickup_hub_id == hub_id) | (Parcel.delivery_hub_id == hub_id))
    city_query = city_query.group_by(Parcel.delivery_city).order_by(func.count(Parcel.id).desc()).limit(5)
    city_res = await db.execute(city_query)
    top_cities = [{"city": row.city, "count": row.count} for row in city_res.all()]

    return {
        "stats": {
            "total_parcels": total,
            "delivered": delivered,
            "pending": stats_row.pending or 0,
            "total_revenue": float(stats_row.revenue or 0)
        },
        "daily_volume": daily_volume,
        "daily_revenue": daily_revenue,
        "success_rate": success_rate,
        "top_cities": top_cities
    }