import uuid
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.payment import Payment
from app.models.parcel import Parcel
from app.schemas.payment import PaymentCreate
from app.utils.config import settings
from fastapi import HTTPException

async def initiate_payment(db: AsyncSession, parcel_id: uuid.UUID, data: PaymentCreate, base_url: str):
    parcel_res = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = parcel_res.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(404, "Parcel not found")

    # Payment record create koro
    new_payment = Payment(
        parcel_id=parcel.id,
        method=data.method,
        amount=data.amount,
        status="pending",
        transaction_id=None
    )
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)

    # Jodi COD hoy, SSLCommerz lagbe na
    if data.method == "cod":
        return {
            "status": "success",
            "redirect_url": None,
            "payment_id": new_payment.id,
            "message": "COD payment initiated"
        }

    # SSLCommerz Init API call
    sslc_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if settings.SSLC_IS_SANDBOX else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
    
    payload = {
        "store_id": settings.SSLC_STORE_ID,
        "store_passwd": settings.SSLC_STORE_PASSWORD,
        "total_amount": data.amount,
        "currency": "BDT",
        "tran_id": f"TRX-{new_payment.id.hex[:8].upper()}", # Unique transaction ID
        "success_url": f"{base_url}/api/v1/payments/success/{new_payment.id}",
        "fail_url": f"{base_url}/api/v1/payments/fail/{new_payment.id}",
        "cancel_url": f"{base_url}/api/v1/payments/cancel/{new_payment.id}",
        "cus_name": "SwiftParcel Customer",
        "cus_email": "customer@example.com",
        "cus_phone": "01700000000",
        "cus_add1": "Dhaka",
        "cus_city": "Dhaka",
        "cus_country": "Bangladesh",
        "shipping_method": "NO",
        "product_name": "Parcel Delivery",
        "product_category": "Courier",
        "product_profile": "general"
    }

    try:
        response = requests.post(sslc_url, data=payload, timeout=10)
        response_data = response.json()
        
        if response_data.get("status") == "SUCCESS":
            # Transaction ID update koro
            new_payment.transaction_id = payload["tran_id"]
            await db.commit()
            
            return {
                "status": "success",
                "redirect_url": response_data.get("GatewayPageURL"),
                "payment_id": new_payment.id,
                "message": "Payment initiated"
            }
        else:
            raise HTTPException(400, f"SSLCommerz Error: {response_data.get('failedreason')}")
            
    except Exception as e:
        raise HTTPException(500, f"Payment Gateway Error: {str(e)}")


async def confirm_payment(db: AsyncSession, payment_id: uuid.UUID, status: str):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(404, "Payment not found")
        
    if payment.status == "paid":
        raise HTTPException(400, "Payment already completed")

    payment.status = status
    await db.commit()
    await db.refresh(payment)
    return payment