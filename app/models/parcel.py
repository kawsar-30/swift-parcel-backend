import uuid
from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base

class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tracking_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    sender_name: Mapped[str] = mapped_column(String(100))
    sender_phone: Mapped[str] = mapped_column(String(20))
    pickup_address: Mapped[str] = mapped_column(String(255))
    
    receiver_name: Mapped[str] = mapped_column(String(100))
    receiver_phone: Mapped[str] = mapped_column(String(20))
    delivery_address: Mapped[str] = mapped_column(String(255))
    delivery_city: Mapped[str] = mapped_column(String(50), index=True)
    
    weight_kg: Mapped[float] = mapped_column(Float)
    parcel_type: Mapped[str] = mapped_column(String(50))
    delivery_type: Mapped[str] = mapped_column(String(20))
    
    cod_amount: Mapped[float] = mapped_column(Float, default=0.0)
    delivery_charge: Mapped[float] = mapped_column(Float)
    total_amount: Mapped[float] = mapped_column(Float)
    
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    
    pickup_zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    delivery_zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    
    pickup_hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    delivery_hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    
    assigned_rider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riders.id"), nullable=True)
    hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["ParcelItem"]] = relationship("ParcelItem", back_populates="parcel", cascade="all, delete-orphan", lazy="selectin")

    # --- Virtual Properties (Ei gulo DB e save hobe na, shudhu read korar jonno) ---
    @property
    def pickup_zone_name(self):
        return getattr(self, "_pickup_zone_name", None)

    @pickup_zone_name.setter
    def pickup_zone_name(self, value):
        self._pickup_zone_name = value

    @property
    def delivery_zone_name(self):
        return getattr(self, "_delivery_zone_name", None)

    @delivery_zone_name.setter
    def delivery_zone_name(self, value):
        self._delivery_zone_name = value

    @property
    def pickup_hub_name(self):
        return getattr(self, "_pickup_hub_name", None)

    @pickup_hub_name.setter
    def pickup_hub_name(self, value):
        self._pickup_hub_name = value

    @property
    def delivery_hub_name(self):
        return getattr(self, "_delivery_hub_name", None)

    @delivery_hub_name.setter
    def delivery_hub_name(self, value):
        self._delivery_hub_name = value