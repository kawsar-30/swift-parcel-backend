from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.database.database import get_db
from app.models.parcel import Parcel
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.invoice_service import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/{parcel_id}")
async def download_invoice(
    parcel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Parcel ta items soho load koro
    result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id).options(selectinload(Parcel.items))
    )
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(404, "Parcel not found")
        
    # Security check (Customer nijer ba admin hole dekhte parbe)
    if current_user.role not in ["admin", "manager"] and parcel.sender_id != current_user.id:
        raise HTTPException(403, "Not authorized to view this invoice")

    pdf_buffer = generate_invoice_pdf(parcel)
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=invoice_{parcel.tracking_id}.pdf"}
    )