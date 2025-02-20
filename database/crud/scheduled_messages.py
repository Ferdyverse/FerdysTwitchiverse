from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import ScheduledMessage, ScheduledMessagePool
import datetime
import random
import logging

logger = logging.getLogger("uvicorn.error.scheduled_messages")

def get_scheduled_messages(db: Session = Depends(get_db)):
    """Retrieve all scheduled messages that are enabled and due to be sent."""
    try:
        return db.query(ScheduledMessage).filter(ScheduledMessage.enabled == True).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve scheduled messages: {e}")
        return []

def add_scheduled_message(db: Session = Depends(get_db), category: str = None, message: str = None, interval: int = 60):
    """Add a scheduled message. Either a message or a category must be provided."""
    if not message and not category:
        raise ValueError("Either `message` or `category` must be provided.")

    try:
        new_schedule = ScheduledMessage(
            message=message,
            category=category,
            interval=interval
        )
        db.add(new_schedule)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to add scheduled message: {e}")
        return {"error": "Database error"}

def update_scheduled_message(
    message_id: int,
    new_message: str,
    new_interval: int,
    new_category: str,
    db: Session = Depends(get_db)
):
    """Update an existing scheduled message in the database."""
    try:
        message = db.query(ScheduledMessage).filter(ScheduledMessage.id == message_id).first()
        if not message:
            return {"error": "Message not found"}

        if new_message:
            message.message = new_message
        if new_category:
            message.category = new_category
        message.interval = new_interval

        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to update scheduled message: {e}")
        db.rollback()
        return {"error": "Database error"}

def remove_scheduled_message(db: Session = Depends(get_db), message_id: int = None):
    """Delete a scheduled message by ID."""
    try:
        deleted = db.query(ScheduledMessage).filter(ScheduledMessage.id == message_id).delete()
        db.commit()
        return deleted > 0
    except Exception as e:
        logger.error(f"❌ Failed to delete scheduled message: {e}")
        return {"error": "Database error"}

def get_random_message_from_category(db: Session = Depends(get_db), category: str = None):
    """Retrieve a random message from a specific category."""
    try:
        messages = db.query(ScheduledMessagePool.message).filter(ScheduledMessagePool.category == category).all()
        return random.choice(messages)[0] if messages else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve random message: {e}")
        return None

def add_message_to_pool(db: Session = Depends(get_db), category: str = None, message: str = None):
    """Add a message to the scheduled message pool."""
    try:
        new_message = ScheduledMessagePool(category=category, message=message)
        db.add(new_message)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to add message to pool: {e}")
        return {"error": "Database error"}

def delete_message_from_pool(db: Session = Depends(get_db), message_id: int = None):
    """Remove a message from the pool by ID."""
    try:
        deleted = db.query(ScheduledMessagePool).filter(ScheduledMessagePool.id == message_id).delete()
        db.commit()
        return {"success": deleted > 0}
    except Exception as e:
        logger.error(f"❌ Failed to delete message from pool: {e}")
        return {"error": "Database error"}

def get_messages_from_pool(db: Session = Depends(get_db), category: str = None):
    """Retrieve all messages from a specific category."""
    try:
        return db.query(ScheduledMessagePool.id, ScheduledMessagePool.message).filter(ScheduledMessagePool.category == category).all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve messages from pool: {e}")
        return []

def get_categories(db: Session = Depends(get_db)):
    """Retrieve a list of all unique categories from ScheduledMessagePool."""
    try:
        categories = db.query(ScheduledMessagePool.category).distinct().all()
        return [category[0] for category in categories]  # Convert tuples to a list of strings
    except Exception as e:
        logger.error(f"❌ Failed to retrieve categories: {e}")
        return []

def update_pool_message(message_id: int = None, new_category: str = None, new_message: str = None, db: Session = Depends(get_db)):
    """Update an existing message in the message pool, including category."""
    try:
        pool_message = db.query(ScheduledMessagePool).filter(ScheduledMessagePool.id == message_id).first()
        if not pool_message:
            return False

        if new_category is not None:
            pool_message.category = new_category
        pool_message.message = new_message

        db.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update pool message: {e}")
        return False

def get_scheduled_message_pool(db: Session = Depends(get_db)):
    """Retrieve all messages from the scheduled message pool."""
    try:
        messages = db.query(ScheduledMessagePool.id, ScheduledMessagePool.category, ScheduledMessagePool.message).all()
        return [dict(msg._mapping) for msg in messages]
    except Exception as e:
        logger.error(f"❌ Failed to retrieve message pool: {e}")
        return []
