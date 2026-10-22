import asyncio
import random
import string
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.utils.config import settings
from app.models.parcel import Parcel
from app.models.parcel_item import ParcelItem
from app.models.status_log import ParcelStatusLog
from app.models.zone import Zone
from app.models.user import User
from app.models.hub import Hub
from app.utils.pricing import calculate_delivery_charge

def generate_tracking_id():
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SP-{date_str}-{suffix}"

async def main():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={'ssl': True})
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Sender khuje ber koro (prothom customer)
        user_res = await db.execute(select(User).where(User.role == "customer").limit(1))
        sender = user_res.scalar_one_or_none()
        if not sender:
            print("Kono customer nai! Age ekjon customer register koro.")
            return

        # 2. Tejgaon ar Mirpur zone khuje ber koro
        tejgaon_res = await db.execute(select(Zone).where(Zone.name.ilike('%Tejgaon%')))
        tejgaon_zone = tejgaon_res.scalar_one_or_none()

        mirpur_res = await db.execute(select(Zone).where(Zone.name.ilike('%Mirpur%')))
        mirpur_zone = mirpur_res.scalar_one_or_none()

        if not tejgaon_zone or not mirpur_zone:
            print("Zone paowa jay nai! Admin panel theke Tejgaon ar Mirpur zone create koro.")
            return

        # 3. Hub gulo khuje ber koro
        tejgaon_hub_res = await db.execute(select(Hub).where(Hub.id == tejgaon_zone.hub_id))
        tejgaon_hub = tejgaon_hub_res.scalar_one_or_none()
        
        mirpur_hub_res = await db.execute(select(Hub).where(Hub.id == mirpur_zone.hub_id))
        mirpur_hub = mirpur_hub_res.scalar_one_or_none()

        if not tejgaon_hub or not mirpur_hub:
            print("Hub paowa jay nai! Zone gulo hub er sathe assign kora ache kina check koro.")
            return

        print(f"Sender: {sender.name}")
        print(f"Pickup Zone: {tejgaon_zone.name} (Hub: {tejgaon_hub.name})")
        print(f"Delivery Zone: {mirpur_zone.name} (Hub: {mirpur_hub.name})")
        print("10 ta parcel create kora hocche...\n")

        # 4. 10 ta parcel create koro
        for i in range(1, 11):
            tracking_id = generate_tracking_id()
            
            # Pricing calculate
            pricing = await calculate_delivery_charge(
                db, 
                weight_kg=1.0, 
                delivery_type="standard", 
                cod_amount=0.0
            )

            parcel = Parcel(
                id=uuid4(),
                tracking_id=tracking_id,
                sender_id=sender.id,
                sender_name=sender.name,
                sender_phone=sender.phone or "01700000000",
                pickup_address=f"Tejgaon, Dhaka (Order #{i})",
                receiver_name=f"Receiver {i}",
                receiver_phone="01800000000",
                delivery_address=f"Mirpur, Dhaka (Address #{i})",
                delivery_city="Dhaka",
                weight_kg=1.0,
                parcel_type="Document",
                delivery_type="standard",
                cod_amount=0.0,
                delivery_charge=pricing["total_amount"],
                total_amount=pricing["total_amount"],
                status="PENDING",
                pickup_zone_id=tejgaon_zone.id,
                delivery_zone_id=mirpur_zone.id,
                pickup_hub_id=tejgaon_hub.id,
                delivery_hub_id=mirpur_hub.id,
                hub_id=None,  # Ekhono hub e pouchay nai
            )
            db.add(parcel)
            await db.flush()

            # Status log
            log = ParcelStatusLog(
                id=uuid4(),
                parcel_id=parcel.id,
                status="PENDING",
                note="Parcel created via seed script",
                updated_by=sender.id
            )
            db.add(log)

        await db.commit()
        print("✅ 10 ta parcel successfully create hoye geche!")
        print("Ekhon Admin/Manager panel theke dekhle pabe.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())