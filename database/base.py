from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    event_type = Column(String, index=True)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    viewer_id = Column(Integer, ForeignKey('viewers.twitch_id'), nullable=True)
    message = Column(String, nullable=False)
    message_id = Column(String, unique=True, nullable=True, index=True)
    stream_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

class OverlayData(Base):
    __tablename__ = "overlay_data"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    value = Column(String)

class Planet(Base):
    __tablename__ = "planets"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    raider_name = Column(String, nullable=False)
    raid_size = Column(Integer, nullable=False)
    angle = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)

class Viewer(Base):
    __tablename__ = "viewers"
    twitch_id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
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
    last_message_time = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

class AdminButton(Base):
    __tablename__ = "admin_buttons"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    action = Column(String, nullable=False)
    data = Column(Text, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    prompt = Column(Boolean, default=False)

class Todo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=False)
    twitch_id = Column(Integer, ForeignKey("viewers.twitch_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    status = Column(String, default="pending")  # "pending" or "completed"

class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=True)
    message = Column(String, nullable=True)
    interval = Column(Integer, nullable=False)
    next_run = Column(DateTime, nullable=False, default=datetime.datetime.now(datetime.timezone.utc))
    enabled = Column(Boolean, default=1)

class ScheduledMessagePool(Base):
    __tablename__ = "scheduled_message_pool"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)
    enabled = Column(Boolean, default=1)
