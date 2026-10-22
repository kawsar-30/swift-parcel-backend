# from pydantic import BaseModel, Field
# from uuid import UUID

# class PricingRuleCreate(BaseModel):
#     from_zone: str = Field(..., min_length=2)
#     to_zone: str = Field(..., min_length=2)
#     base_price: float = Field(..., gt=0)
#     per_kg_price: float = Field(..., gt=0)
#     express_multiplier: float = Field(1.5, gt=1.0)

# class PricingRuleResponse(BaseModel):
#     id: UUID
#     from_zone: str
#     to_zone: str
#     base_price: float
#     per_kg_price: float
#     express_multiplier: float

#     class Config:
#         from_attributes = True

from pydantic import BaseModel, Field
from uuid import UUID

class PricingRuleCreate(BaseModel):
    from_hub_id: UUID
    to_hub_id: UUID
    base_price: float = Field(..., gt=0)
    per_kg_price: float = Field(..., gt=0)
    express_multiplier: float = Field(1.5, gt=1.0)

class PricingRuleResponse(BaseModel):
    id: UUID
    from_hub_id: UUID
    to_hub_id: UUID
    base_price: float
    per_kg_price: float
    express_multiplier: float
    
    # Frontend e dekhানোর jonno hub er nam
    from_hub_name: str | None = None
    to_hub_name: str | None = None

    class Config:
        from_attributes = True