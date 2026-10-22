from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    parcel_id: UUID | None = None

class LocationResponse(BaseModel):
    rider_id: UUID
    latitude: float
    longitude: float
    updated_at: datetime

    class Config:
        from_attributes = True