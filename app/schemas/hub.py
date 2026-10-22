from pydantic import BaseModel, Field
from uuid import UUID

class HubCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    city: str = Field(..., min_length=2, max_length=50)
    address: str = Field(..., min_length=5, max_length=255)
    manager_id: UUID | None = None

class HubResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    manager_id: UUID | None

    class Config:
        from_attributes = True


class HubDetailsResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    manager_id: UUID | None
    manager_name: str | None = None
    manager_phone: str | None = None
    riders_count: int = 0
    total_parcels: int = 0
    pending_parcels: int = 0
    delivered_parcels: int = 0