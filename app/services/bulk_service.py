import pandas as pd
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.parcel import Parcel
from app.models.zone import Zone
from app.models.hub import Hub
from app.utils.pricing import calculate_delivery_charge
from app.services.parcel_service import generate_tracking_id
from fastapi import HTTPException

async def process_bulk_csv(db: AsyncSession, file_content: bytes, sender_id):
    try:
        df = pd.read_csv(BytesIO(file_content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

    # Required columns check koro
    required_cols = [
        "sender_name", "sender_phone", "pickup_address", "pickup_zone",
        "receiver_name", "receiver_phone", "delivery_address", "delivery_city", "delivery_zone",
        "weight_kg", "parcel_type", "delivery_type"
    ]
    
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing column in CSV: {col}")

    successful = 0
    failed = 0
    errors = []

    for index, row in df.iterrows():
        try:
            # Tracking ID generate koro
            tracking_id = generate_tracking_id()
            
            # CSV থেকে জোনের নাম নাও
            pickup_zone_name = str(row["pickup_zone"]).strip()
            delivery_zone_name = str(row["delivery_zone"]).strip()

            # ডেটাবেস থেকে জোনের আইডি খোঁজা
            p_zone_res = await db.execute(select(Zone).where(Zone.name == pickup_zone_name))
            pickup_zone = p_zone_res.scalar_one_or_none()
            
            d_zone_res = await db.execute(select(Zone).where(Zone.name == delivery_zone_name))
            delivery_zone = d_zone_res.scalar_one_or_none()

            if not pickup_zone:
                raise ValueError(f"Invalid pickup zone: {pickup_zone_name}")
            if not delivery_zone:
                raise ValueError(f"Invalid delivery zone: {delivery_zone_name}")

            # Pricing calculate koro
            cod_amount = float(row.get("cod_amount", 0.0)) if pd.notna(row.get("cod_amount")) else 0.0
            pricing = await calculate_delivery_charge(
                db, 
                weight_kg=float(row["weight_kg"]),
                delivery_type=str(row["delivery_type"]),
                cod_amount=cod_amount,
                pickup_zone_id=pickup_zone.id,
                delivery_zone_id=delivery_zone.id
            )

            new_parcel = Parcel(
                tracking_id=tracking_id,
                sender_id=sender_id,
                sender_name=str(row["sender_name"]),
                sender_phone=str(row["sender_phone"]),
                pickup_address=str(row["pickup_address"]),
                receiver_name=str(row["receiver_name"]),
                receiver_phone=str(row["receiver_phone"]),
                delivery_address=str(row["delivery_address"]),
                delivery_city=str(row["delivery_city"]),
                weight_kg=float(row["weight_kg"]),
                parcel_type=str(row["parcel_type"]),
                delivery_type=str(row["delivery_type"]),
                cod_amount=cod_amount,
                delivery_charge=pricing["total_amount"] - pricing["cod_fee"],
                total_amount=pricing["total_amount"],
                status="PENDING",
                pickup_zone_id=pickup_zone.id,
                delivery_zone_id=delivery_zone.id,
                pickup_hub_id=pickup_zone.hub_id,
                delivery_hub_id=delivery_zone.hub_id
            )
            db.add(new_parcel)
            successful += 1
        except Exception as e:
            failed += 1
            errors.append(f"Row {index+1}: {str(e)}")

    await db.commit()
    
    return {
        "message": "Bulk upload processed",
        "successful": successful,
        "failed": failed,
        "errors": errors[:10] # Max 10 error dekhabo
    }