import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base

class RiderLocation(Base):
    __tablename__ = "rider_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riders.id"), index=True)
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("parcels.id"), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())