from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.database import get_db
from app.models.parcel import Parcel
from app.models.status_log import ParcelStatusLog
from pydantic import BaseModel
from datetime import datetime
from typing import List

router = APIRouter(prefix="/track", tags=["Public Tracking"])

class StatusLogResponse(BaseModel):
    status: str
    note: str | None
    location: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class TrackingResponse(BaseModel):
    tracking_id: str
    status: str
    receiver_name: str
    delivery_city: str
    created_at: datetime
    timeline: List[StatusLogResponse]

@router.get("/{tracking_id}", response_model=TrackingResponse)
async def track_parcel(tracking_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parcel).where(Parcel.tracking_id == tracking_id))
    parcel = result.scalar_one_or_none()

    if not parcel:
        raise HTTPException(status_code=404, detail="Tracking ID not found")

    # Status logs ber koro
    logs_result = await db.execute(
        select(ParcelStatusLog)
        .where(ParcelStatusLog.parcel_id == parcel.id)
        .order_by(ParcelStatusLog.created_at.asc())
    )
    logs = logs_result.scalars().all()

    return {
        "tracking_id": parcel.tracking_id,
        "status": parcel.status,
        "receiver_name": parcel.receiver_name,
        "delivery_city": parcel.delivery_city,
        "created_at": parcel.created_at,
        "timeline": logs
    }