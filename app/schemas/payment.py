from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class PaymentCreate(BaseModel):
    method: str = Field(..., pattern="^(bkash|card|cod)$")
    amount: float = Field(..., gt=0)

class PaymentResponse(BaseModel):
    id: UUID
    parcel_id: UUID
    method: str
    amount: float
    status: str
    transaction_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentInitiateResponse(BaseModel):
    message: str
    payment_id: UUID
    amount: float
    method: str
    redirect_url: str | None = None