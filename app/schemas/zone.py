from pydantic import BaseModel, Field
from uuid import UUID

class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    hub_id: UUID | None = None

class ZoneResponse(BaseModel):
    id: UUID
    name: str
    city: str
    hub_id: UUID | None

    class Config:
        from_attributes = True