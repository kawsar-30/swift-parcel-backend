from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, join
from uuid import UUID
from app.models.rider import Rider
from app.models.user import User
from app.models.hub import Hub

async def get_riders_by_manager_hub(db: AsyncSession, manager_id: UUID):
    # Manager er hub ber koro
    hub_res = await db.execute(select(Hub).where(Hub.manager_id == manager_id))
    hub = hub_res.scalar_one_or_none()
    
    if not hub:
        return []

    # Oi hub er sob rider ber koro
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
        }
        for r in riders
    ]