import datetime
import logging
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.chat")

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
        user_db = couchdb_client.get_db("viewers")

        # Retrieve last `limit` chat messages sorted by timestamp
        messages = []
        for row in db.view("_all_docs", include_docs=True):
            doc = row["doc"]
            if doc.get("type") == "chat_message":
                messages.append(doc)

        # Sort messages by timestamp (newest first) and limit results
        messages = sorted(messages, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

        formatted_messages = []
        for doc in messages:
            viewer_id = str(doc.get("viewer_id", ""))  # Ensure viewer_id is a string
            user = user_db.get(viewer_id, {})

            formatted_messages.append({
                "message": doc.get("message", ""),
                "timestamp": doc.get("timestamp", ""),
                "message_id": doc.get("_id", ""),
                "twitch_id": viewer_id,
                "username": user.get("display_name", "Unknown"),
                "avatar": user.get("profile_image_url", ""),
                "user_color": user.get("color", "#FFFFFF"),
                "badges": user.get("badges", ""),
            })

        return formatted_messages

    except Exception as e:
        logger.error(f"❌ Failed to retrieve chat messages: {e}")
        return []
