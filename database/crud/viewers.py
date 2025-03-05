from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import Viewer, ViewerStats

def get_viewer(twitch_id: int, db: Session = Depends(get_db)):
    """Retrieve a viewer by Twitch ID."""
    try:
        return db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
    except Exception as e:
        print(f"❌ Failed to retrieve viewer: {e}")
        return None

def save_viewer(twitch_id: int, login: str, display_name: str, profile_image_url: str, db: Session = Depends(get_db)):
    """Save or update a viewer."""
    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
        if viewer:
            viewer.login = login
            viewer.display_name = display_name
            viewer.profile_image_url = profile_image_url
        else:
            viewer = Viewer(
                twitch_id=twitch_id,
                login=login,
                display_name=display_name,
                profile_image_url=profile_image_url
            )
            db.add(viewer)
        db.commit()
        db.refresh(viewer)
        return viewer
    except Exception as e:
        print(f"❌ Error saving viewer: {e}")
        db.rollback()
        return None

def get_viewer_stats(twitch_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific viewer's data along with chat stats."""
    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
        if not viewer:
            return None

        stream_stats = db.query(ViewerStats).filter(ViewerStats.twitch_id == twitch_id).all()

        return {
            "twitch_id": viewer.twitch_id,
            "login": viewer.login,
            "display_name": viewer.display_name,
            "total_chat_messages": viewer.total_chat_messages,
            "total_used_emotes": viewer.total_used_emotes,
            "total_replies": viewer.total_replies,
            "per_stream_stats": [
                {
                    "stream_id": stat.stream_id,
                    "chat_messages": stat.chat_messages,
                    "used_emotes": stat.used_emotes,
                    "replies": stat.replies,
                    "last_message_time": stat.last_message_time
                }
                for stat in stream_stats
            ]
        }
    except Exception as e:
        print(f"❌ Failed to retrieve viewer stats: {e}")
        return None

def update_viewer_stats(twitch_id: int, stream_id: str, message: str, emotes_used: int, is_reply: bool, db: Session = Depends(get_db)):
    """Update viewer stats without needing an explicit db session."""

    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
        if viewer:
            viewer.total_chat_messages += 1
            viewer.total_used_emotes += emotes_used
            viewer.total_replies += 1 if is_reply else 0
            db.commit()

        stats = db.query(ViewerStats).filter(ViewerStats.twitch_id == twitch_id, ViewerStats.stream_id == stream_id).first()

        if stats:
            stats.chat_messages += 1
            stats.used_emotes += emotes_used
            stats.replies += 1 if is_reply else 0
            stats.last_message_time = datetime.datetime.utcnow()
        else:
            stats = ViewerStats(
                twitch_id=twitch_id,
                stream_id=stream_id,
                chat_messages=1,
                used_emotes=emotes_used,
                replies=1 if is_reply else 0
            )
            db.add(stats)

        db.commit()
        return stats
    except Exception as e:
        print(f"❌ Failed to update viewer stats: {e}")
