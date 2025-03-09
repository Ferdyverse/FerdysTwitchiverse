from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy import case
from database.base import Event, Viewer
import datetime

async def save_event(event_type: str, viewer_id: int = None, message: str = "", db: AsyncSession = None):
    """Save an event asynchronously."""
    try:
        event = Event(event_type=event_type, viewer_id=viewer_id, message=message, timestamp=datetime.datetime.utcnow())
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event
    except Exception as e:
        print(f"❌ Error saving event: {e}")
        await db.rollback()
        return None

async def get_recent_events(limit: int = 50, db: AsyncSession = None):
    """Retrieve the last `limit` events asynchronously."""
    try:
        query = select(
            Event.id,
            Event.message,
            Event.event_type,
            Event.timestamp,
            case(
                (Viewer.display_name.isnot(None), Viewer.display_name),
                else_="Unknown"
            ).label("username"),
            Viewer.profile_image_url.label("avatar"),
            Viewer.color.label("user_color"),
            Viewer.badges.label("badges"),
            Event.viewer_id.label("twitch_id")
        ).outerjoin(Viewer, Event.viewer_id == Viewer.twitch_id).order_by(Event.timestamp.desc()).limit(limit)

        result = await db.execute(query)
        return result.mappings().all()
    except Exception as e:
        print(f"❌ Error retrieving events: {e}")
        return []
