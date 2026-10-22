from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.database.database import get_db
from app.schemas.parcel import ParcelCreate, ParcelResponse, ParcelEstimateRequest, ParcelEstimateResponse
from app.services.parcel_service import create_parcel
from app.utils.pricing import calculate_delivery_charge
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.parcel import Parcel
from app.models.status_log import ParcelStatusLog

router = APIRouter(prefix="/parcels", tags=["Parcels"])

@router.post("/estimate", response_model=ParcelEstimateResponse)
async def estimate_price(data: ParcelEstimateRequest, db: AsyncSession = Depends(get_db)):
    pricing = await calculate_delivery_charge(
        db,
        weight_kg=data.weight_kg,
        delivery_type=data.delivery_type,
        cod_amount=data.cod_amount,
        pickup_zone_id=data.pickup_zone_id,    # <-- Notun
        delivery_zone_id=data.delivery_zone_id # <-- Notun
    )
    return pricing

@router.post("", response_model=ParcelResponse, status_code=status.HTTP_201_CREATED)
async def book_parcel(
    data: ParcelCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    parcel = await create_parcel(db, current_user.id, data)
    return parcel

@router.get("", response_model=list[ParcelResponse])
async def get_my_parcels(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(Parcel)
        .where(Parcel.sender_id == current_user.id)
        .options(selectinload(Parcel.items))
        .order_by(Parcel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    parcels = result.scalars().all()
    
    # Payment status add koro
    from app.models.payment import Payment
    response_data = []
    for p in parcels:
        # Latest payment check koro
        payment_res = await db.execute(
            select(Payment)
            .where(Payment.parcel_id == p.id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        payment = payment_res.scalar_one_or_none()
        
        p_dict = {
            "id": p.id,
            "tracking_id": p.tracking_id,
            "sender_name": p.sender_name,
            "receiver_name": p.receiver_name,
            "delivery_city": p.delivery_city,
            "weight_kg": p.weight_kg,
            "delivery_charge": p.delivery_charge,
            "total_amount": p.total_amount,
            "status": p.status,
            "created_at": p.created_at,
            "items": p.items if p.items else [],
            "pickup_zone_id": p.pickup_zone_id,
            "delivery_zone_id": p.delivery_zone_id,
            "pickup_hub_id": p.pickup_hub_id,
            "delivery_hub_id": p.delivery_hub_id,
            "payment_status": payment.status if payment else None,  # <-- Notun
        }
        response_data.append(p_dict)
    
    return response_data
@router.post("/{parcel_id}/cancel")
async def cancel_parcel(
    parcel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
        
    if parcel.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this parcel")
        
    if parcel.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING parcels can be cancelled")
        
    parcel.status = "CANCELLED"
    
    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status="CANCELLED",
        note="Cancelled by customer",
        updated_by=current_user.id
    )
    db.add(log)
    await db.commit()
    
    return {"message": "Parcel cancelled successfully"}