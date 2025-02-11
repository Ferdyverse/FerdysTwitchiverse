from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
import datetime

DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Event(Base):
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ChatMessage(Base):
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
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
    twitch_id = Column(Integer, primary_key=True)  # Twitch ID as primary key
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    login = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    account_type = Column(String)
    broadcaster_type = Column(String)
    profile_image_url = Column(String, nullable=False)
    account_age = Column(String, nullable=False)
    follower_date = Column(DateTime)
    subscriber_date = Column(DateTime)

    # Overall stats
    total_chat_messages = Column(Integer, default=0)
    total_used_emotes = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)

class ViewerStats(Base):
    __tablename__ = "viewer_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    twitch_id = Column(Integer, ForeignKey("viewers.twitch_id"), nullable=False)
    stream_id = Column(String, nullable=False)  # Unique ID for each stream
    chat_messages = Column(Integer, default=0)
    used_emotes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    last_message_time = Column(DateTime, default=datetime.datetime.utcnow)

class AdminButton(Base):
    __tablename__ = "admin_buttons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False)  # Button text
    action = Column(String, nullable=False)  # Associated action (e.g., "show_icon")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database."""
    Base.metadata.create_all(bind=engine)

def get_chat_messages(db: Session = Depends(get_db)):
    return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(50).all()

def get_data(key: str, db: Session):
    """Retrieve a specific key's value from the overlay_data table."""
    overlay_data = db.query(OverlayData).filter(OverlayData.key == key).first()
    return overlay_data.value if overlay_data else None

def get_planets(db: Session):
    return db.query(Planet).order_by(Planet.date.desc()).all()

def save_event(event_type: str, viewer_id: int, message: str, db: Session):
    event = Event(event_type=event_type, viewer_id=viewer_id, message=message)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def get_recent_events(db: Session, limit: int = 50):
    return db.query(
        Event.id,
        Event.event_type,
        Event.message,
        Event.timestamp,
        Viewer.display_name.label("username")  # Get username from viewers table
    ).join(Viewer, Event.viewer_id == Viewer.twitch_id, isouter=True) \
    .order_by(Event.timestamp.desc()).limit(limit).all()

def save_chat_message(viewer_id: int, message: str, db: Session):
    chat_message = ChatMessage(viewer_id=viewer_id, message=message)
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    return chat_message

def get_recent_chat_messages(db: Session, limit: int = 50):
    return db.query(
        ChatMessage.id,
        ChatMessage.message,
        ChatMessage.timestamp,
        Viewer.display_name.label("username")  # Get username from viewers table
    ).join(Viewer, ChatMessage.viewer_id == Viewer.twitch_id, isouter=True) \
    .order_by(ChatMessage.timestamp.desc()).limit(limit).all()

def save_overlay_data(key: str, value: str, db: Session):
    overlay_data = db.query(OverlayData).filter_by(key=key).first()
    if overlay_data:
        overlay_data.value = value
    else:
        overlay_data = OverlayData(key=key, value=value)
        db.add(overlay_data)
    db.commit()
    return overlay_data

def get_overlay_data(key: str, db: Session):
    overlay_data = db.query(OverlayData).filter_by(key=key).first()
    return overlay_data.value if overlay_data else None

def save_data(key: str, value: str, db: Session):
    """Save or update data in the overlay_data table."""
    return save_overlay_data(key, value, db)

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float, db: Session):
    planet = Planet(raider_name=raider_name, raid_size=raid_size, angle=angle, distance=distance)
    db.add(planet)
    db.commit()
    db.refresh(planet)
    return planet

def clear_planets(db: Session):
    db.query(Planet).delete()
    db.commit()

def save_viewer(twitch_id: int, login: str, display_name: str, account_type: str, broadcaster_type: str,
                profile_image_url: str, account_age: str, follower_date: datetime.datetime,
                subscriber_date: datetime.datetime, db: Session):
    """Save or update viewer data."""
    viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()

    if viewer:
        # Update only if new data is available
        viewer.display_name = display_name or viewer.display_name
        viewer.account_type = account_type or viewer.account_type
        viewer.broadcaster_type = broadcaster_type or viewer.broadcaster_type
        viewer.profile_image_url = profile_image_url or viewer.profile_image_url
        viewer.account_age = account_age or viewer.account_age
        viewer.follower_date = follower_date if follower_date else viewer.follower_date
        viewer.subscriber_date = subscriber_date if subscriber_date else viewer.subscriber_date
    else:
        # Insert new viewer data
        viewer = Viewer(
            twitch_id=twitch_id,
            login=login,
            display_name=display_name,
            account_type=account_type,
            broadcaster_type=broadcaster_type,
            profile_image_url=profile_image_url,
            account_age=account_age,
            follower_date=follower_date,
            subscriber_date=subscriber_date
        )
        db.add(viewer)

    db.commit()
    db.refresh(viewer)
    return viewer


def get_viewer_stats(twitch_id: int, db: Session):
    """Retrieve a specific viewer's data along with chat stats."""
    viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()

    if not viewer:
        return None

    # Get per-stream stats
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


def update_viewer_stats(twitch_id: int, stream_id: str, message: str, emotes_used: int, is_reply: bool, db: Session):
    """Update viewer stats for both overall and per-stream tracking."""

    # Update overall stats in `viewers`
    viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
    if viewer:
        viewer.total_chat_messages += 1
        viewer.total_used_emotes += emotes_used
        viewer.total_replies += 1 if is_reply else 0
        db.commit()

    # Update per-stream stats in `viewer_stats`
    stats = db.query(ViewerStats).filter(ViewerStats.twitch_id == twitch_id, ViewerStats.stream_id == stream_id).first()

    if stats:
        stats.chat_messages += 1
        stats.used_emotes += emotes_used
        stats.replies += 1 if is_reply else 0
        stats.last_message_time = datetime.datetime.utcnow()
    else:
        # Create new entry for this stream
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
