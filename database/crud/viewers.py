import datetime
import logging
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.viewers")


def get_viewer(twitch_id: int):
    """Retrieve a viewer by Twitch ID from CouchDB."""
    try:
        db = couchdb_client.get_db("viewers")
        doc_id = f"viewer_{twitch_id}"

        if doc_id in db:
            return db[doc_id]

        return None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve viewer: {e}")
        return None


def save_viewer(twitch_id: int, login: str, display_name: str, profile_image_url: str):
    """Save or update a viewer in CouchDB."""
    try:
        db = couchdb_client.get_db("viewers")
        doc_id = f"viewer_{twitch_id}"

        viewer = db.get(doc_id, {})

        viewer.update({
            "_id": doc_id,
            "type": "viewer",
            "twitch_id": twitch_id,
            "login": login,
            "display_name": display_name,
            "profile_image_url": profile_image_url,
            "total_chat_messages": viewer.get("total_chat_messages", 0),
            "total_used_emotes": viewer.get("total_used_emotes", 0),
            "total_replies": viewer.get("total_replies", 0)
        })

        db.save(viewer)
        return viewer
    except Exception as e:
        logger.error(f"❌ Error saving viewer: {e}")
        return None


def get_viewer_stats(twitch_id: int):
    """Retrieve a specific viewer's data along with chat stats from CouchDB."""
    try:
        db = couchdb_client.get_db("viewers")
        doc_id = f"viewer_{twitch_id}"

        viewer = db.get(doc_id)
        if not viewer:
            return None

        return {
            "twitch_id": viewer["twitch_id"],
            "login": viewer["login"],
            "display_name": viewer["display_name"],
            "total_chat_messages": viewer.get("total_chat_messages", 0),
            "total_used_emotes": viewer.get("total_used_emotes", 0),
            "total_replies": viewer.get("total_replies", 0),
            "per_stream_stats": viewer.get("stream_stats", [])
        }
    except Exception as e:
        logger.error(f"❌ Failed to retrieve viewer stats: {e}")
        return None


def update_viewer_stats(twitch_id: int, stream_id: str, message: str, emotes_used: int, is_reply: str):
    """Update viewer stats in CouchDB."""
    try:
        db = couchdb_client.get_db("viewers")
        doc_id = f"viewer_{twitch_id}"

        if doc_id not in db:
            return None

        viewer = db[doc_id]

        # Global statistics
        viewer["total_chat_messages"] = viewer.get("total_chat_messages", 0) + 1
        viewer["total_used_emotes"] = viewer.get("total_used_emotes", 0) + emotes_used

        # Handle replies
        if is_reply:
            viewer["total_replies"] = viewer.get("total_replies", 0) + 1

        # Per-stream statistics
        stream_stats = viewer.get("stream_stats", [])
        stream_record = next((stat for stat in stream_stats if stat["stream_id"] == stream_id), None)

        if stream_record:
            stream_record["chat_messages"] += 1
            stream_record["used_emotes"] += emotes_used
            if is_reply:
                stream_record["replies"] += 1
            stream_record["last_message_time"] = datetime.datetime.utcnow().isoformat()
        else:
            stream_stats.append({
                "stream_id": stream_id,
                "chat_messages": 1,
                "used_emotes": emotes_used,
                "replies": 1 if is_reply else 0,
                "last_message_time": datetime.datetime.utcnow().isoformat()
            })

        viewer["stream_stats"] = stream_stats
        db.save(viewer)

        return viewer
    except Exception as e:
        logger.error(f"❌ Failed to update viewer stats: {e}")
        return None
