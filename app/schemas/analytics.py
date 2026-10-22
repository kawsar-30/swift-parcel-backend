from pydantic import BaseModel

class DailyVolumeResponse(BaseModel):
    date: str
    count: int

class DailyRevenueResponse(BaseModel):
    date: str
    revenue: float

class DeliverySuccessResponse(BaseModel):
    total_parcels: int
    delivered_parcels: int
    success_rate: float

class TopCityResponse(BaseModel):
    city: str
    count: int