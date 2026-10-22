from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional

from app.database.database import get_db
from app.models.parcel import Parcel
from app.models.hub import Hub
from app.models.user import User
from app.api.dependencies import require_role
from app.schemas.analytics import DailyVolumeResponse, DailyRevenueResponse, DeliverySuccessResponse, TopCityResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/daily-volume", response_model=list[DailyVolumeResponse])
async def daily_volume(
    days: int = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    # Date range determine koro
    if start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) + timedelta(days=1)
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)

    query = (
        select(
            func.date(Parcel.created_at).label("date"),
            func.count(Parcel.id).label("count")
        )
        .where(Parcel.created_at >= start, Parcel.created_at < end)
        .group_by(func.date(Parcel.created_at))
        .order_by(func.date(Parcel.created_at).asc())
    )

    # Manager hole shudhu tar hub er data
    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                (Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)
            )
        else:
            return []

    result = await db.execute(query)
    return [{"date": str(row.date), "count": row.count} for row in result.all()]


@router.get("/daily-revenue", response_model=list[DailyRevenueResponse])
async def daily_revenue(
    days: int = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    if start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) + timedelta(days=1)
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)

    query = (
        select(
            func.date(Parcel.created_at).label("date"),
            func.sum(Parcel.total_amount).label("revenue")
        )
        .where(Parcel.created_at >= start, Parcel.created_at < end)
        .group_by(func.date(Parcel.created_at))
        .order_by(func.date(Parcel.created_at).asc())
    )

    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                (Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)
            )
        else:
            return []

    result = await db.execute(query)
    return [{"date": str(row.date), "revenue": float(row.revenue or 0)} for row in result.all()]


@router.get("/success-rate", response_model=DeliverySuccessResponse)
async def success_rate(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    query = select(func.count(Parcel.id))

    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                (Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)
            )
        else:
            return {"total_parcels": 0, "delivered_parcels": 0, "success_rate": 0.0}

    total = await db.scalar(query)
    
    # Delivered
    delivered_query = query.where(Parcel.status == "DELIVERED")
    delivered = await db.scalar(delivered_query)

    rate = round((delivered / total * 100), 2) if total and total > 0 else 0.0
    return {
        "total_parcels": total or 0,
        "delivered_parcels": delivered or 0,
        "success_rate": rate
    }


@router.get("/top-cities", response_model=list[TopCityResponse])
async def top_cities(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "manager"))
):
    query = (
        select(
            Parcel.delivery_city.label("city"),
            func.count(Parcel.id).label("count")
        )
        .group_by(Parcel.delivery_city)
        .order_by(func.count(Parcel.id).desc())
        .limit(limit)
    )

    if current_user.role == "manager":
        hub_res = await db.execute(select(Hub).where(Hub.manager_id == current_user.id))
        hub = hub_res.scalar_one_or_none()
        if hub:
            query = query.where(
                (Parcel.pickup_hub_id == hub.id) | (Parcel.delivery_hub_id == hub.id)
            )
        else:
            return []

    result = await db.execute(query)
    return [{"city": row.city, "count": row.count} for row in result.all()]