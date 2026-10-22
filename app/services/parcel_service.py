import random
import string
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.parcel import Parcel
from app.models.parcel_item import ParcelItem
from app.models.status_log import ParcelStatusLog
from app.models.zone import Zone
from app.models.hub import Hub
from app.schemas.parcel import ParcelCreate
from app.utils.pricing import calculate_delivery_charge

def generate_tracking_id() -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SP-{date_str}-{suffix}"

async def create_parcel(db: AsyncSession, sender_id: UUID, data: ParcelCreate) -> Parcel:
    pricing = await calculate_delivery_charge(
        db, 
        weight_kg=data.weight_kg, 
        delivery_type=data.delivery_type, 
        cod_amount=data.cod_amount,
        pickup_zone_id=data.pickup_zone_id,    # <-- Notun
        delivery_zone_id=data.delivery_zone_id # <-- Notun
    )
    
    tracking_id = generate_tracking_id()
    while True:
        result = await db.execute(select(Parcel).where(Parcel.tracking_id == tracking_id))
        if not result.scalar_one_or_none():
            break
        tracking_id = generate_tracking_id()

    # Smart Routing Logic
    pickup_hub_id = None
    delivery_hub_id = None
    pickup_zone = None
    delivery_zone = None

    if data.pickup_zone_id:
        zone_res = await db.execute(select(Zone).where(Zone.id == data.pickup_zone_id))
        pickup_zone = zone_res.scalar_one_or_none()
        if pickup_zone:
            pickup_hub_id = pickup_zone.hub_id

    if data.delivery_zone_id:
        zone_res = await db.execute(select(Zone).where(Zone.id == data.delivery_zone_id))
        delivery_zone = zone_res.scalar_one_or_none()
        if delivery_zone:
            delivery_hub_id = delivery_zone.hub_id

    parcel = Parcel(
        tracking_id=tracking_id,
        sender_id=sender_id,
        sender_name=data.sender_name,
        sender_phone=data.sender_phone,
        pickup_address=data.pickup_address,
        receiver_name=data.receiver_name,
        receiver_phone=data.receiver_phone,
        delivery_address=data.delivery_address,
        delivery_city=data.delivery_city,
        weight_kg=data.weight_kg,
        parcel_type=data.parcel_type,
        delivery_type=data.delivery_type,
        cod_amount=data.cod_amount,
        delivery_charge=pricing["total_amount"] - pricing["cod_fee"],
        total_amount=pricing["total_amount"],
        status="PENDING",
        pickup_zone_id=data.pickup_zone_id,
        delivery_zone_id=data.delivery_zone_id,
        pickup_hub_id=pickup_hub_id,
        delivery_hub_id=delivery_hub_id
    )
    
    db.add(parcel)
    await db.flush() 
    
    for item_data in data.items:
        new_item = ParcelItem(
            parcel_id=parcel.id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price
        )
        db.add(new_item)
    
    log = ParcelStatusLog(
        parcel_id=parcel.id,
        status="PENDING",
        note="Parcel created and pending for assignment",
        updated_by=sender_id
    )
    db.add(log)
    await db.commit()
    
    # Full parcel reload with names
    result = await db.execute(
        select(Parcel).where(Parcel.id == parcel.id).options(selectinload(Parcel.items))
    )
    full_parcel = result.scalar_one()

    # Hub nam ber koro
    if pickup_hub_id:
        hub_res = await db.execute(select(Hub).where(Hub.id == pickup_hub_id))
        pickup_hub = hub_res.scalar_one_or_none()
        full_parcel.pickup_hub_name = pickup_hub.name if pickup_hub else None

    if delivery_hub_id:
        hub_res = await db.execute(select(Hub).where(Hub.id == delivery_hub_id))
        delivery_hub = hub_res.scalar_one_or_none()
        full_parcel.delivery_hub_name = delivery_hub.name if delivery_hub else None

    # Zone nam set koro
    full_parcel.pickup_zone_name = pickup_zone.name if pickup_zone else None
    full_parcel.delivery_zone_name = delivery_zone.name if delivery_zone else None
    full_parcel.pickup_zone_name = pickup_zone.name if pickup_zone else None
    full_parcel.delivery_zone_name = delivery_zone.name if delivery_zone else None

    if pickup_hub_id:
        hub_res = await db.execute(select(Hub).where(Hub.id == pickup_hub_id))
        pickup_hub = hub_res.scalar_one_or_none()
        full_parcel.pickup_hub_name = pickup_hub.name if pickup_hub else None

    if delivery_hub_id:
        hub_res = await db.execute(select(Hub).where(Hub.id == delivery_hub_id))
        delivery_hub = hub_res.scalar_one_or_none()
        full_parcel.delivery_hub_name = delivery_hub.name if delivery_hub else None
    return full_parcel