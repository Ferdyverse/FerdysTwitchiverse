from sqlalchemy.orm import Session, aliased
from fastapi import Depends
from sqlalchemy import case
from database.session import get_db
from database.base import Event, Viewer
import datetime

def save_event(event_type: str, viewer_id: int = None, message: str = "", db: Session = Depends(get_db)):
    """Save an event."""
    try:
        event = Event(event_type=event_type, viewer_id=viewer_id, message=message, timestamp=datetime.datetime.utcnow())
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as e:
        print(f"❌ Error saving event: {e}")
        db.rollback()
        return None

def get_recent_events(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve the last `limit` events."""
    # Ensure we fetch ALL events, even if viewer_id is NULL
    events = db.query(
        Event.id,
        Event.message,
        Event.event_type,
        Event.timestamp,
        case(
            (Viewer.display_name.isnot(None), Viewer.display_name),  # If viewer exists, use display_name
            else_="Unknown"  # Otherwise, return "Unknown"
        ).label("username"),
        Viewer.profile_image_url.label("avatar"),
        Viewer.color.label("user_color"),
        Viewer.badges.label("badges"),
        Event.viewer_id.label("twitch_id")
    ).outerjoin(Viewer, Event.viewer_id == Viewer.twitch_id).order_by(Event.timestamp.desc()).limit(limit).all()

    return events
