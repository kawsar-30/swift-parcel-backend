from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.database import get_db
from app.models.pricing_rule import PricingRule
from app.models.hub import Hub
from app.models.zone import Zone

router = APIRouter(prefix="/public", tags=["Public Pricing"])

@router.get("/pricing-rules")
async def get_public_pricing_rules(db: AsyncSession = Depends(get_db)):
    # Hub-to-Hub Rules fetch kora
    rules_res = await db.execute(select(PricingRule))
    rules = rules_res.scalars().all()
    
    pricing_data = []
    for rule in rules:
        f_hub = await db.execute(select(Hub).where(Hub.id == rule.from_hub_id))
        t_hub = await db.execute(select(Hub).where(Hub.id == rule.to_hub_id))
        from_hub = f_hub.scalar_one_or_none()
        to_hub = t_hub.scalar_one_or_none()
        
        pricing_data.append({
            "id": rule.id,
            "from_hub_name": from_hub.name if from_hub else "Unknown",
            "to_hub_name": to_hub.name if to_hub else "Unknown",
            "base_price": rule.base_price,
            "per_kg_price": rule.per_kg_price,
            "express_multiplier": rule.express_multiplier,
        })
        
    # Zones fetch kora (Customer der zone list dekhানোর jonno)
    zones_res = await db.execute(select(Zone))
    zones = zones_res.scalars().all()
    zone_data = [{"id": z.id, "name": z.name, "city": z.city} for z in zones]

    return {
        "hub_rules": pricing_data,
        "zones": zone_data
    }