from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.hub import Hub
from app.models.user import User
from app.schemas.hub import HubCreate
from fastapi import HTTPException

async def create_hub(db: AsyncSession, data: HubCreate) -> Hub:
    # Manager check koro (jodi deya thake)
    if data.manager_id:
        result = await db.execute(select(User).where(User.id == data.manager_id))
        manager = result.scalar_one_or_none()
        if not manager or manager.role != "manager":
            raise HTTPException(status_code=400, detail="Invalid manager ID")

    new_hub = Hub(
        name=data.name,
        city=data.city,
        address=data.address,
        manager_id=data.manager_id
    )
    db.add(new_hub)
    await db.commit()
    await db.refresh(new_hub)
    return new_hub