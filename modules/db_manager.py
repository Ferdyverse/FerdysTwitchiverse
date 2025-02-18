from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import json
import logging

DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger("uvicorn.error.db_manager")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    event_type = Column(String, index=True)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    message = Column(String, nullable=False)
    message_id = Column(String, unique=True, nullable=True, index=True)
    stream_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class OverlayData(Base):
    __tablename__ = "overlay_data"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    value = Column(String)

class Planet(Base):
    __tablename__ = "planets"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    raider_name = Column(String, nullable=False)
    raid_size = Column(Integer, nullable=False)
    angle = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)

class Viewer(Base):
    __tablename__ = "viewers"
    twitch_id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    login = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    account_type = Column(String)
    broadcaster_type = Column(String)
    profile_image_url = Column(String, nullable=False)
    account_age = Column(String, nullable=False)
    follower_date = Column(DateTime)
    subscriber_date = Column(DateTime)
    color = Column(String)
    badges = Column(String)
    total_chat_messages = Column(Integer, default=0)
    total_used_emotes = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)

class ViewerStats(Base):
    __tablename__ = "viewer_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    twitch_id = Column(Integer, ForeignKey("viewers.twitch_id"), nullable=False)
    stream_id = Column(String, nullable=False)
    chat_messages = Column(Integer, default=0)
    used_emotes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    last_message_time = Column(DateTime, default=datetime.datetime.utcnow)

class AdminButton(Base):
    __tablename__ = "admin_buttons"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    action = Column(String, nullable=False)
    data = Column(Text, nullable=True)

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=False)
    twitch_id = Column(Integer, ForeignKey("viewers.twitch_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")  # "pending" or "completed"

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def get_chat_messages(limit: int = 50):
    """Retrieve the last `limit` chat messages from the database without requiring an explicit db session."""
    db = SessionLocal()
    try:
        return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve chat messages: {e}")
        return []
    finally:
        db.close()

def get_data(key: str):
    """Retrieve a specific key's value from the overlay_data table."""
    db = SessionLocal()
    try:
        overlay_data = db.query(OverlayData).filter(OverlayData.key == key).first()
        return overlay_data.value if overlay_data else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve overlay data: {e}")
        return None
    finally:
        db.close()

def get_planets():
    """Retrieve all planets from the database."""
    db = SessionLocal()
    try:
        return db.query(Planet).order_by(Planet.date.desc()).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve planets: {e}")
        return []
    finally:
        db.close()

def save_event(event_type: str, viewer_id: int = None, message: str = ""):
    """Save an event in the database without requiring an explicit db session."""
    db = next(get_db())

    try:
        event = Event(event_type=event_type, viewer_id=viewer_id, message=message)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as e:
        logger.error(f"❌ Failed to save event: {e}")
    finally:
        db.close()

def get_recent_events(limit: int = 50):
    """Retrieve the last `limit` events from the database."""
    db = SessionLocal()
    try:
        return db.query(
            Event.id,
            Event.event_type,
            Event.message,
            Event.timestamp,
            Viewer.display_name.label("username")  # Get username from viewers table
        ).join(Viewer, Event.viewer_id == Viewer.twitch_id, isouter=True) \
        .order_by(Event.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve recent events: {e}")
        return []
    finally:
        db.close()

def save_chat_message(viewer_id: int, message: str, message_id: str, stream_id: str):
    """Save a chat message without needing an explicit database session."""
    db = next(get_db())

    try:
        chat_message = ChatMessage(
            viewer_id=viewer_id,
            message=message,
            message_id=message_id,
            stream_id=stream_id
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        return chat_message
    except Exception as e:
        logger.error(f"❌ Failed to save chat message: {e}")
    finally:
        db.close()

def get_recent_chat_messages(limit: int = 50):
    """Retrieve the last `limit` chat messages from the database."""
    db = next(get_db())

    try:
        return db.query(
            ChatMessage.id,
            ChatMessage.message,
            ChatMessage.timestamp,
            Viewer.display_name.label("username"),
            ChatMessage.viewer_id.label("twitch_id")
        ).join(Viewer, ChatMessage.viewer_id == Viewer.twitch_id, isouter=True) \
        .order_by(ChatMessage.timestamp.desc()) \
        .limit(limit).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve chat messages: {e}")
        return []
    finally:
        db.close()

def save_overlay_data(key: str, value: str):
    """Save or update overlay data."""
    db = SessionLocal()
    try:
        overlay_data = db.query(OverlayData).filter_by(key=key).first()
        if overlay_data:
            overlay_data.value = value
        else:
            overlay_data = OverlayData(key=key, value=value)
            db.add(overlay_data)
        db.commit()
        return overlay_data
    except Exception as e:
        logger.error(f"❌ Failed to save overlay data: {e}")
    finally:
        db.close()

def get_overlay_data(key: str):
    """Retrieve overlay data."""
    db = SessionLocal()
    try:
        overlay_data = db.query(OverlayData).filter_by(key=key).first()
        return overlay_data.value if overlay_data else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve overlay data: {e}")
        return None
    finally:
        db.close()

def save_data(key: str, value: str):
    """Save or update data in the overlay_data table."""
    db = SessionLocal()
    try:
        return save_overlay_data(key, value)
    except Exception as e:
        logger.error(f"❌ Failed to save data: {e}")
    finally:
        db.close()

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float):
    """Save a planet record."""
    db = SessionLocal()
    try:
        planet = Planet(raider_name=raider_name, raid_size=raid_size, angle=angle, distance=distance)
        db.add(planet)
        db.commit()
        db.refresh(planet)
        return planet
    except Exception as e:
        logger.error(f"❌ Failed to save planet: {e}")
    finally:
        db.close()

def clear_planets():
    """Delete all planets from the database."""
    db = SessionLocal()
    try:
        db.query(Planet).delete()
        db.commit()
    except Exception as e:
        logger.error(f"❌ Failed to clear planets: {e}")
    finally:
        db.close()

def save_viewer(twitch_id: int, login: str, display_name: str, account_type: str, broadcaster_type: str,
                profile_image_url: str, account_age: str, follower_date: datetime.datetime,
                subscriber_date: datetime.datetime, color: str, badges: str):
    """Save or update viewer data without needing an explicit db session."""
    db = next(get_db())

    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()

        if viewer:
            viewer.display_name = display_name or viewer.display_name
            viewer.account_type = account_type or viewer.account_type
            viewer.broadcaster_type = broadcaster_type or viewer.broadcaster_type
            viewer.profile_image_url = profile_image_url or viewer.profile_image_url
            viewer.account_age = account_age or viewer.account_age
            viewer.follower_date = follower_date if follower_date else viewer.follower_date
            viewer.subscriber_date = subscriber_date if subscriber_date else viewer.subscriber_date
            viewer.color = color or viewer.color
            viewer.badges = badges or viewer.badges
        else:
            viewer = Viewer(
                twitch_id=twitch_id,
                login=login,
                display_name=display_name,
                account_type=account_type,
                broadcaster_type=broadcaster_type,
                profile_image_url=profile_image_url,
                account_age=account_age,
                follower_date=follower_date,
                subscriber_date=subscriber_date,
                color=color,
                badges=badges
            )
            db.add(viewer)

        db.commit()
        db.refresh(viewer)
        return viewer
    except Exception as e:
        logger.error(f"❌ Failed to save viewer: {e}")
    finally:
        db.close()

def get_viewer_stats(twitch_id: int):
    """Retrieve a specific viewer's data along with chat stats."""
    db = SessionLocal()
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
        logger.error(f"❌ Failed to retrieve viewer stats: {e}")
        return None
    finally:
        db.close()

def update_viewer_stats(twitch_id: int, stream_id: str, message: str, emotes_used: int, is_reply: bool):
    """Update viewer stats without needing an explicit db session."""
    db = next(get_db())

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
        logger.error(f"❌ Failed to update viewer stats: {e}")
    finally:
        db.close()


def cleanup_old_data(days: int = 5):
    """Delete chat messages and events older than the specified number of days."""
    db = SessionLocal()
    try:
        # Calculate the date threshold
        threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        # Delete old chat messages
        deleted_chats = db.query(ChatMessage).filter(ChatMessage.timestamp < threshold_date).delete()
        logger.info(f"🗑️ Deleted {deleted_chats} old chat messages.")

        # Delete old events
        deleted_events = db.query(Event).filter(Event.timestamp < threshold_date).delete()
        logger.info(f"🗑️ Deleted {deleted_events} old events.")

        save_event("system_cleanup", None, f"Deleted {deleted_chats} chat messages and {deleted_events} events.")

        db.commit()
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

def save_todo(text: str, twitch_id: int):
    """Save a new ToDo in the database, linked to a viewer."""
    db = SessionLocal()
    try:
        todo = Todo(text=text, twitch_id=twitch_id)
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo
    except Exception as e:
        logger.error(f"❌ Failed to save ToDo: {e}")
    finally:
        db.close()

def get_todos():
    """Retrieve all ToDos with viewer info."""
    db = SessionLocal()
    try:
        return db.query(
            Todo.id, Todo.text, Todo.created_at, Todo.status,
            Viewer.display_name.label("username"),
            Todo.twitch_id
        ).join(Viewer, Todo.twitch_id == Viewer.twitch_id).order_by(Todo.created_at.desc()).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve ToDos: {e}")
        return []
    finally:
        db.close()

def complete_todo(todo_id: int):
    """Mark a ToDo as completed."""
    db = SessionLocal()
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if todo:
            todo.status = "completed"
            db.commit()
            db.refresh(todo)
            return todo
    except Exception as e:
        logger.error(f"❌ Failed to update ToDo: {e}")
    finally:
        db.close()
