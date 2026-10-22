# # from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy import select
# # from app.models.pricing_rule import PricingRule

# # async def get_pricing_rule(db: AsyncSession, from_zone: str = "Inside City", to_zone: str = "Inside City"):
# #     result = await db.execute(
# #         select(PricingRule)
# #         .where(PricingRule.from_zone == from_zone, PricingRule.to_zone == to_zone)
# #     )
# #     rule = result.scalar_one_or_none()
    
# #     # Jodi database e rule na thake, default return koro
# #     if not rule:
# #         return {"base_price": 60.0, "per_kg_price": 20.0, "express_multiplier": 1.5}
        
# #     return {
# #         "base_price": rule.base_price,
# #         "per_kg_price": rule.per_kg_price,
# #         "express_multiplier": rule.express_multiplier
# #     }

# # async def calculate_delivery_charge(db: AsyncSession, weight_kg: float, delivery_type: str, cod_amount: float = 0.0):
# #     rule = await get_pricing_rule(db)
    
# #     base_price = rule["base_price"]
# #     per_kg_price = rule["per_kg_price"]
# #     express_multiplier = rule["express_multiplier"]
# #     cod_fee_percentage = 0.01

# #     charge = base_price
    
# #     if weight_kg > 1.0:
# #         extra_weight = weight_kg - 1.0
# #         charge += extra_weight * per_kg_price
        
# #     if delivery_type == "express":
# #         charge = charge * express_multiplier
        
# #     cod_fee = cod_amount * cod_fee_percentage
# #     total_amount = charge + cod_fee
    
# #     return {
# #         "base_price": base_price,
# #         "weight_charge": max(0, (weight_kg - 1.0) * per_kg_price),
# #         "express_charge": (charge - base_price) if delivery_type == "express" else 0,
# #         "cod_fee": cod_fee,
# #         "total_amount": round(total_amount, 2)
# #     }


# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from app.models.pricing_rule import PricingRule
# from app.models.zone import Zone

# async def get_pricing_rule(db: AsyncSession, pickup_zone_id, delivery_zone_id):
#     # ডিফল্ট ভ্যালু
#     default_rule = {"base_price": 60.0, "per_kg_price": 20.0, "express_multiplier": 1.5}
    
#     if not pickup_zone_id or not delivery_zone_id:
#         return default_rule

#     # জোনের নাম বের করা
#     pickup_zone_res = await db.execute(select(Zone).where(Zone.id == pickup_zone_id))
#     pickup_zone = pickup_zone_res.scalar_one_or_none()
    
#     delivery_zone_res = await db.execute(select(Zone).where(Zone.id == delivery_zone_id))
#     delivery_zone = delivery_zone_res.scalar_one_or_none()

#     if not pickup_zone or not delivery_zone:
#         return default_rule

#     # ডেটাবেস থেকে রুল খোঁজা
#     result = await db.execute(
#         select(PricingRule)
#         .where(PricingRule.from_zone == pickup_zone.name)
#         .where(PricingRule.to_zone == delivery_zone.name)
#     )
#     rule = result.scalar_one_or_none()
    
#     if not rule:
#         return default_rule
        
#     return {
#         "base_price": rule.base_price,
#         "per_kg_price": rule.per_kg_price,
#         "express_multiplier": rule.express_multiplier
#     }

# async def calculate_delivery_charge(
#     db: AsyncSession, 
#     weight_kg: float, 
#     delivery_type: str, 
#     cod_amount: float = 0.0,
#     pickup_zone_id = None,
#     delivery_zone_id = None
# ):
#     rule = await get_pricing_rule(db, pickup_zone_id, delivery_zone_id)
    
#     base_price = rule["base_price"]
#     per_kg_price = rule["per_kg_price"]
#     express_multiplier = rule["express_multiplier"]
#     cod_fee_percentage = 0.01

#     charge = base_price
    
#     if weight_kg > 1.0:
#         extra_weight = weight_kg - 1.0
#         charge += extra_weight * per_kg_price
        
#     if delivery_type == "express":
#         charge = charge * express_multiplier
        
#     cod_fee = cod_amount * cod_fee_percentage
#     total_amount = charge + cod_fee
    
#     return {
#         "base_price": base_price,
#         "weight_charge": max(0, (weight_kg - 1.0) * per_kg_price),
#         "express_charge": (charge - base_price) if delivery_type == "express" else 0,
#         "cod_fee": cod_fee,
#         "total_amount": round(total_amount, 2)
#     }

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pricing_rule import PricingRule
from app.models.zone import Zone

async def get_pricing_rule(db: AsyncSession, pickup_zone_id, delivery_zone_id):
    # ডিফল্ট রুল
    default_same_hub = {"base_price": 60.0, "per_kg_price": 20.0, "express_multiplier": 1.5}
    default_diff_hub = {"base_price": 120.0, "per_kg_price": 30.0, "express_multiplier": 1.5}
    
    if not pickup_zone_id or not delivery_zone_id:
        return default_same_hub

    # জোন থেকে হাব আইডি বের করা
    p_zone_res = await db.execute(select(Zone).where(Zone.id == pickup_zone_id))
    pickup_zone = p_zone_res.scalar_one_or_none()
    
    d_zone_res = await db.execute(select(Zone).where(Zone.id == delivery_zone_id))
    delivery_zone = d_zone_res.scalar_one_or_none()

    if not pickup_zone or not delivery_zone or not pickup_zone.hub_id or not delivery_zone.hub_id:
        return default_same_hub

    pickup_hub_id = pickup_zone.hub_id
    delivery_hub_id = delivery_zone.hub_id

    # ডেটাবেস থেকে রুল খোঁজা
    result = await db.execute(
        select(PricingRule)
        .where(PricingRule.from_hub_id == pickup_hub_id)
        .where(PricingRule.to_hub_id == delivery_hub_id)
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        # যদি রুল না থাকে, চেক করব হাব এক নাকি আলাদা
        if pickup_hub_id == delivery_hub_id:
            return default_same_hub
        else:
            return default_diff_hub
        
    return {
        "base_price": rule.base_price,
        "per_kg_price": rule.per_kg_price,
        "express_multiplier": rule.express_multiplier
    }

async def calculate_delivery_charge(
    db: AsyncSession, 
    weight_kg: float, 
    delivery_type: str, 
    cod_amount: float = 0.0,
    pickup_zone_id = None,
    delivery_zone_id = None
):
    rule = await get_pricing_rule(db, pickup_zone_id, delivery_zone_id)
    
    base_price = rule["base_price"]
    per_kg_price = rule["per_kg_price"]
    express_multiplier = rule["express_multiplier"]
    cod_fee_percentage = 0.01

    charge = base_price
    
    if weight_kg > 1.0:
        extra_weight = weight_kg - 1.0
        charge += extra_weight * per_kg_price
        
    if delivery_type == "express":
        charge = charge * express_multiplier
        
    cod_fee = cod_amount * cod_fee_percentage
    total_amount = charge + cod_fee
    
    return {
        "base_price": base_price,
        "weight_charge": max(0, (weight_kg - 1.0) * per_kg_price),
        "express_charge": (charge - base_price) if delivery_type == "express" else 0,
        "cod_fee": cod_fee,
        "total_amount": round(total_amount, 2)
    }