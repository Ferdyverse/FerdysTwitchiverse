from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends
from database.session import get_db
from database.base import ChatMessage, Viewer
import datetime

async def get_chat_messages(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Retrieve the last `limit` chat messages from the database asynchronously."""
    try:
        result = await db.execute(
            select(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        print(f"❌ Failed to retrieve chat messages: {e}")
        return []

async def delete_chat_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a chat message by ID from the database asynchronously."""
    try:
        result = await db.execute(select(ChatMessage).filter(ChatMessage.message_id == message_id))
        message = result.scalars().first()

        if not message:
            return {"error": "Message not found"}

        await db.delete(message)
        await db.commit()
        return {"success": True}
    except Exception as e:
        print(f"❌ Failed to delete chat message: {e}")
        await db.rollback()
        return {"error": "Database error"}

async def save_chat_message(viewer_id: int, message: str, message_id: str, stream_id: str, db: AsyncSession = Depends(get_db)):
    """Save a chat message asynchronously."""
    try:
        chat_message = ChatMessage(
            viewer_id=viewer_id,
            message=message,
            message_id=message_id,
            stream_id=stream_id
        )
        db.add(chat_message)
        await db.commit()
        await db.refresh(chat_message)
        return chat_message
    except Exception as e:
        print(f"❌ Failed to save chat message: {e}")
        await db.rollback()
        return None

async def get_recent_chat_messages(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Retrieve the last `limit` chat messages, including user details asynchronously."""
    try:
        result = await db.execute(
            select(
                ChatMessage.id,
                ChatMessage.message,
                ChatMessage.timestamp,
                ChatMessage.message_id,
                Viewer.display_name.label("username"),
                Viewer.profile_image_url.label("avatar"),
                Viewer.color.label("user_color"),
                Viewer.badges.label("badges"),
                ChatMessage.viewer_id.label("twitch_id")
            )
            .join(Viewer, ChatMessage.viewer_id == Viewer.twitch_id, isouter=True)
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
        )
        return result.all()
    except Exception as e:
        print(f"❌ Failed to retrieve chat messages: {e}")
        return []
