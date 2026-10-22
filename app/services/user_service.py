from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.rider import Rider
from app.models.hub import Hub
from app.schemas.auth import InternalUserCreate
from app.utils.security import hash_password
from fastapi import HTTPException

async def create_internal_user(db: AsyncSession, data: InternalUserCreate):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role,
        profile_picture=data.profile_picture,
        nid_number=data.nid_number,
        address=data.address,
        is_active=True
    )
    db.add(new_user)
    await db.flush()

    if data.role == "rider":
        if not data.hub_id:
            raise HTTPException(status_code=400, detail="Hub ID is required for riders")
            
        new_rider = Rider(
            user_id=new_user.id,
            hub_id=data.hub_id,
            vehicle_type=data.vehicle_type or "Bike",
            is_available=True,
            rider_type=data.rider_type or "both"  # <-- Notun
        )
        db.add(new_rider)

    if data.role == "manager":
        if not data.hub_id:
            raise HTTPException(status_code=400, detail="Hub ID is required for managers")
            
        hub_res = await db.execute(select(Hub).where(Hub.id == data.hub_id))
        hub = hub_res.scalar_one_or_none()
        if not hub:
            raise HTTPException(status_code=404, detail="Hub not found")
            
        hub.manager_id = new_user.id

    await db.commit()
    await db.refresh(new_user)
    return new_user