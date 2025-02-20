from database.session import SessionLocal
from database.base import ChatMessage, Viewer
import datetime

def save_chat_message(viewer_id: int, message: str, message_id: str, stream_id: str):
    """Save a chat message."""
    db = SessionLocal()
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
        return None
    finally:
        db.close()

def get_recent_chat_messages(limit: int = 50):
    """Retrieve the last `limit` chat messages."""
    db = SessionLocal()
    try:
        messages = db.query(
            ChatMessage.id,
            ChatMessage.message,
            ChatMessage.timestamp,
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
    finally:
        db.close()
