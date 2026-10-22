import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(50))
    
    # Hub er sathe link (One-to-Many)
    hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    hub = relationship("Hub", backref="zones")