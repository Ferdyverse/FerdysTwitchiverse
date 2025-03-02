from sqlalchemy.orm import Session
from fastapi import Depends
from database.session import get_db
from database.base import ChatMessage, Viewer
import datetime

def get_chat_messages(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve the last `limit` chat messages from the database."""
    try:
        messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
        return messages
    except Exception as e:
        print(f"❌ Failed to retrieve chat messages: {e}")
        return []


def delete_chat_message(message_id: int, db: Session = Depends(get_db)):
    """Delete a chat message by ID from the database."""
    try:
        message = db.query(ChatMessage).filter(ChatMessage.message_id == message_id).first()
        if not message:
            return {"error": "Message not found"}

        db.delete(message)
        db.commit()
        return {"success": True}
    except Exception as e:
        print(f"❌ Failed to delete chat message: {e}")
        db.rollback()
        return {"error": "Database error"}

def save_chat_message(viewer_id: int, message: str, message_id: str, stream_id: str, db: Session = Depends(get_db)):
    """Save a chat message."""
    try:
        chat_message = ChatMessage(
            viewer_id=viewer_id, message=message, message_id=message_id, stream_id=stream_id,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        return chat_message
    except Exception as e:
        print(f"❌ Error saving chat message: {e}")
        db.rollback()
        return None

def get_recent_chat_messages(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve the last `limit` chat messages, including user details."""
    try:
        messages = db.query(
            ChatMessage.id,
            ChatMessage.message,
            ChatMessage.timestamp,
            ChatMessage.message_id,
            Viewer.display_name.label("username"),
            Viewer.profile_image_url.label("avatar"),
            Viewer.color.label("user_color"),
            Viewer.badges.label("badges"),
            ChatMessage.viewer_id.label("twitch_id")
        ).join(Viewer, ChatMessage.viewer_id == Viewer.twitch_id, isouter=True) \
        .order_by(ChatMessage.timestamp.desc()) \
        .limit(limit).all()

        return messages
    except Exception as e:
        print(f"❌ Failed to retrieve chat messages: {e}")
        return []
