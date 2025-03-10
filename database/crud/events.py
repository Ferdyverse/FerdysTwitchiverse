import datetime
import logging
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.events")

def save_event(event_type: str, viewer_id: str = None, message: str = ""):
    """Save an event in CouchDB."""
    try:
        db = couchdb_client.get_db("events")
        event = {
            "_id": f"event_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            "type": "event",
            "event_type": event_type,
            "viewer_id": viewer_id,
            "message": message,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        db.save(event)
        return event
    except Exception as e:
        logger.error(f"❌ Error saving event: {e}")
        return None


def get_recent_events(limit: int = 50):
    """Retrieve the last `limit` events from CouchDB."""
    try:
        db = couchdb_client.get_db("events")
        viewer_db = couchdb_client.get_db("viewers")

        events = []

        # Sort documents by timestamp and limit results
        for doc_id in sorted(db, key=lambda x: db[x]["timestamp"], reverse=True)[:limit]:
            doc = db[doc_id]
            if doc.get("type") == "event":
                user = viewer_db.get(doc["viewer_id"], {}) if doc.get("viewer_id") else {}

                events.append({
                    "event_id": doc["_id"],
                    "message": doc.get("message", ""),
                    "event_type": doc["event_type"],
                    "timestamp": doc["timestamp"],
                    "username": user.get("display_name", "Unknown"),
                    "avatar": user.get("profile_image_url", ""),
                    "user_color": user.get("color", "#FFFFFF"),
                    "badges": user.get("badges", ""),
                    "twitch_id": doc.get("viewer_id")
                })
        return events
    except Exception as e:
        logger.error(f"❌ Failed to retrieve events: {e}")
        return []
