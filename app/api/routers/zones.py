from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database.database import get_db
from app.models.zone import Zone
from app.models.hub import Hub
from app.schemas.zone import ZoneCreate, ZoneResponse
from app.api.dependencies import require_role
from app.models.user import User
from fastapi import HTTPException

router = APIRouter(prefix="/zones", tags=["Zones"])

@router.post("", response_model=ZoneResponse)
async def create_zone(
    data: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    new_zone = Zone(**data.model_dump())
    db.add(new_zone)
    await db.commit()
    await db.refresh(new_zone)
    return new_zone

@router.get("", response_model=list[ZoneResponse])
async def get_zones(
    db: AsyncSession = Depends(get_db)
    # Kono role check nai, public route
):
    result = await db.execute(select(Zone).order_by(Zone.name.asc()))
    return result.scalars().all()