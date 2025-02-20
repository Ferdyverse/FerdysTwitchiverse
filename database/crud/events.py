from sqlalchemy.orm import Session
from fastapi import Depends
from database.session import get_db
from database.base import Event
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
    return db.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()
