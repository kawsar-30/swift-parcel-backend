# import uuid
# from sqlalchemy import String, Float
# from sqlalchemy.orm import Mapped, mapped_column
# from app.database.database import Base

# class PricingRule(Base):
#     __tablename__ = "pricing_rules"

#     id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
#     from_zone: Mapped[str] = mapped_column(String(50)) # e.g., Inside City
#     to_zone: Mapped[str] = mapped_column(String(50))
#     base_price: Mapped[float] = mapped_column(Float)
#     per_kg_price: Mapped[float] = mapped_column(Float)
#     express_multiplier: Mapped[float] = mapped_column(Float, default=1.5)


import uuid
from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base

class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    from_hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id"), nullable=False)
    to_hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id"), nullable=False)
    
    base_price: Mapped[float] = mapped_column(Float)
    per_kg_price: Mapped[float] = mapped_column(Float)
    express_multiplier: Mapped[float] = mapped_column(Float, default=1.5)