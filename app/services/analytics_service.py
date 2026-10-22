from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.parcel import Parcel

async def get_daily_volume(db: AsyncSession, days: int = 7):
    # Last 7 days er daily parcel count
    start_date = datetime.utcnow() - timedelta(days=days)
    query = (
        select(
            func.date(Parcel.created_at).label("date"),
            func.count(Parcel.id).label("count")
        )
        .where(Parcel.created_at >= start_date)
        .group_by(func.date(Parcel.created_at))
        .order_by(func.date(Parcel.created_at).asc())
    )
    result = await db.execute(query)
    return [{"date": str(row.date), "count": row.count} for row in result.all()]

async def get_daily_revenue(db: AsyncSession, days: int = 7):
    start_date = datetime.utcnow() - timedelta(days=days)
    query = (
        select(
            func.date(Parcel.created_at).label("date"),
            func.sum(Parcel.total_amount).label("revenue")
        )
        .where(Parcel.created_at >= start_date)
        .group_by(func.date(Parcel.created_at))
        .order_by(func.date(Parcel.created_at).asc())
    )
    result = await db.execute(query)
    return [{"date": str(row.date), "revenue": float(row.revenue or 0)} for row in result.all()]

async def get_delivery_success_rate(db: AsyncSession):
    total = await db.scalar(select(func.count(Parcel.id)))
    delivered = await db.scalar(select(func.count(Parcel.id)).where(Parcel.status == "DELIVERED"))
    return {
        "total_parcels": total,
        "delivered_parcels": delivered,
        "success_rate": round((delivered / total * 100), 2) if total > 0 else 0.0
    }

async def get_top_cities(db: AsyncSession, limit: int = 5):
    query = (
        select(
            Parcel.delivery_city.label("city"),
            func.count(Parcel.id).label("count")
        )
        .group_by(Parcel.delivery_city)
        .order_by(func.count(Parcel.id).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [{"city": row.city, "count": row.count} for row in result.all()]