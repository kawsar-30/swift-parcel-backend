import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base

class Rider(Base):
    __tablename__ = "riders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id"))
    vehicle_type: Mapped[str] = mapped_column(String(50))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notun add kora holo
    rider_type: Mapped[str] = mapped_column(String(20), default="both")