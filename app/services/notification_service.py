import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification

async def create_notification(db: AsyncSession, user_id: uuid.UUID, title: str, message: str):
    new_notification = Notification(
        user_id=user_id,
        title=title,
        message=message
    )
    db.add(new_notification)
    await db.commit()
    await db.refresh(new_notification)
    return new_notification