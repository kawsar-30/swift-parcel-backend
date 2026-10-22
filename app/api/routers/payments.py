from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database.database import get_db
from app.schemas.payment import PaymentCreate, PaymentInitiateResponse
from app.services.payment_service import initiate_payment, confirm_payment
from app.api.dependencies import get_current_user
from app.models.user import User
from app.utils.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/{parcel_id}/initiate", response_model=PaymentInitiateResponse)
async def create_payment(
    parcel_id: UUID,
    data: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Request theke base url nao (local e localhost, production e real domain)
    base_url = str(request.base_url).rstrip("/")
    
    result = await initiate_payment(db, parcel_id, data, base_url)
    
    return {
        "message": result["message"],
        "payment_id": result["payment_id"],
        "amount": data.amount,
        "method": data.method,
        "redirect_url": result["redirect_url"]
    }

# --- SSLCommerz Callback URLs ---

@router.post("/success/{payment_id}")
async def payment_success(payment_id: UUID, db: AsyncSession = Depends(get_db)):
    # SSLCommerz theke success hole ei url e hit korbe
    await confirm_payment(db, payment_id, "paid")
    # Frontend er success page e redirect koro
    return RedirectResponse(url="http://localhost:3000/payment/success")

@router.post("/fail/{payment_id}")
async def payment_fail(payment_id: UUID, db: AsyncSession = Depends(get_db)):
    await confirm_payment(db, payment_id, "failed")
    return RedirectResponse(url="http://localhost:3000/payment/fail")

@router.post("/cancel/{payment_id}")
async def payment_cancel(payment_id: UUID, db: AsyncSession = Depends(get_db)):
    await confirm_payment(db, payment_id, "failed")
    return RedirectResponse(url="http://localhost:3000/payment/cancel")