from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)
    password: str = Field(..., min_length=6, max_length=50)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    role: str
    profile_picture: str | None = None
    nid_number: str | None = None
    address: str | None = None

    model_config = ConfigDict(from_attributes=True)

class InternalUserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(manager|rider)$")
    profile_picture: str | None = None
    nid_number: str | None = None
    address: str | None = None
    hub_id: UUID | None = None
    vehicle_type: str | None = None
    rider_type: str | None = "both"  # <-- Notun

class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    profile_picture: str | None = None
    nid_number: str | None = None
    address: str | None = None