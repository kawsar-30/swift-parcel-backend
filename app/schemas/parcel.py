from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ParcelItemCreate(BaseModel):
    item_name: str = Field(..., min_length=2)
    quantity: int = Field(1, gt=0)
    unit_price: float = Field(0.0, ge=0)

class ParcelItemResponse(BaseModel):
    id: UUID
    item_name: str
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True

class ParcelCreate(BaseModel):
    sender_name: str = Field(..., min_length=2)
    sender_phone: str = Field(..., min_length=10)
    pickup_address: str = Field(..., min_length=5)
    
    receiver_name: str = Field(..., min_length=2)
    receiver_phone: str = Field(..., min_length=10)
    delivery_address: str = Field(..., min_length=5)
    delivery_city: str = Field(..., min_length=2)
    
    weight_kg: float = Field(..., gt=0)
    parcel_type: str = Field(...)
    delivery_type: str = Field(..., pattern="^(standard|express)$")
    cod_amount: float = Field(0.0, ge=0)
    
    pickup_zone_id: UUID | None = None
    delivery_zone_id: UUID | None = None
    
    items: list[ParcelItemCreate] = []

class ParcelEstimateRequest(BaseModel):
    weight_kg: float = Field(..., gt=0)
    delivery_type: str = Field(..., pattern="^(standard|express)$")
    cod_amount: float = Field(0.0, ge=0)
    pickup_zone_id: UUID | None = None   # <-- Notun
    delivery_zone_id: UUID | None = None # <-- Notun

class ParcelResponse(BaseModel):
    id: UUID
    tracking_id: str
    sender_name: str
    receiver_name: str
    delivery_city: str
    weight_kg: float
    delivery_charge: float
    total_amount: float
    status: str
    created_at: datetime
    items: list[ParcelItemResponse] = []
    
    pickup_zone_id: UUID | None = None
    delivery_zone_id: UUID | None = None
    pickup_hub_id: UUID | None = None
    delivery_hub_id: UUID | None = None

    # Notun add kora holo (nam gulo dekhano)
    pickup_zone_name: str | None = None
    delivery_zone_name: str | None = None
    pickup_hub_name: str | None = None
    delivery_hub_name: str | None = None

    payment_status: str | None = None 

    class Config:
        from_attributes = True

class ParcelEstimateResponse(BaseModel):
    base_price: float
    weight_charge: float
    express_charge: float
    cod_fee: float
    total_amount: float
   