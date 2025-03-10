import datetime
import logging
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.chat")


def get_chat_messages(limit: int = 50):
    """Retrieve the last `limit` chat messages from CouchDB."""
    try:
        db = couchdb_client.get_db("chat")
        messages = [
            db[doc_id] for doc_id in sorted(db, key=lambda x: db[x]["timestamp"], reverse=True)[:limit]
        ]
        return messages
    except Exception as e:
        logger.error(f"❌ Failed to retrieve chat messages: {e}")
        return []


def delete_chat_message(message_id: str):
    """Delete a chat message by ID from CouchDB."""
    try:
        db = couchdb_client.get_db("chat")
        if message_id in db:
            db.delete(db[message_id])
            return {"success": True}
        return {"error": "Message not found"}
    except Exception as e:
        logger.error(f"❌ Failed to delete chat message: {e}")
        return {"error": "Database error"}


def save_chat_message(viewer_id: str, message: str, message_id: str, stream_id: str):
    """Save a chat message in CouchDB."""
    try:
        db = couchdb_client.get_db("chat")
        chat_message = {
            "_id": message_id,
            "type": "chat_message",
            "viewer_id": viewer_id,
            "message": message,
            "stream_id": stream_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        db.save(chat_message)
        return chat_message
    except Exception as e:
        logger.error(f"❌ Error saving chat message: {e}")
        return None


def get_recent_chat_messages(limit: int = 50):
    """Retrieve the last `limit` chat messages including user details."""
    try:
        db = couchdb_client.get_db("chat")
        messages = []
        for doc_id in sorted(db, key=lambda x: db[x]["timestamp"], reverse=True)[:limit]:
            doc = db[doc_id]
            if doc.get("type") == "chat_message":
                user_db = couchdb_client.get_db("viewers")
                user = user_db.get(doc["viewer_id"], {})
                messages.append({
                    "message": doc["message"],
                    "timestamp": doc["timestamp"],
                    "message_id": doc["_id"],
                    "twitch_id": doc["viewer_id"],
                    "username": user.get("display_name", "Unknown"),
                    "avatar": user.get("profile_image_url", ""),
                    "user_color": user.get("color", "#FFFFFF"),
                    "badges": user.get("badges", ""),
                })
        return messages
    except Exception as e:
        logger.error(f"❌ Failed to retrieve chat messages: {e}")
        return []
