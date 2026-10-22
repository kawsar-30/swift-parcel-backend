from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.bulk_service import process_bulk_csv

router = APIRouter(prefix="/bulk", tags=["Bulk Upload"])

@router.post("/upload-csv")
async def upload_parcels_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = await file.read()
    result = await process_bulk_csv(db, content, current_user.id)
    return result