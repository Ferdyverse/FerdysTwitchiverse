from database.session import SessionLocal
from database.base import Event
import datetime

def save_event(event_type: str, viewer_id: int = None, message: str = ""):
    """Save an event."""
    db = SessionLocal()
    try:
        event = Event(event_type=event_type, viewer_id=viewer_id, message=message, timestamp=datetime.datetime.utcnow())
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as e:
        print(f"❌ Error saving event: {e}")
        return None
    finally:
        db.close()

def get_recent_events(limit: int = 50):
    """Retrieve the last `limit` events."""
    db = SessionLocal()
    try:
        return db.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()
    except Exception as e:
        print(f"❌ Failed to retrieve recent events: {e}")
        return []
    finally:
        db.close()
