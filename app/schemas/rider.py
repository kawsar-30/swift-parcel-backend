from pydantic import BaseModel
from uuid import UUID

class RiderResponse(BaseModel):
    id: UUID
    user_id: UUID
    hub_id: UUID
    vehicle_type: str
    is_available: bool

    class Config:
        from_attributes = True

class RiderWithUserResponse(BaseModel):
    # Rider info + User info (name, phone, pic)
    id: UUID
    name: str
    email: str
    phone: str | None
    profile_picture: str | None
    hub_id: UUID
    vehicle_type: str
    is_available: bool