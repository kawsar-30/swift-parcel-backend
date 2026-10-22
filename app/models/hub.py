import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base

class Hub(Base):
    __tablename__ = "hubs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(50), index=True)
    address: Mapped[str] = mapped_column(String(255))
    
    manager_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)