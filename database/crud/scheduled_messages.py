from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.base import ScheduledMessagePool
import random
import logging

logger = logging.getLogger("uvicorn.error.scheduled_messages")

async def get_random_message_from_category(db: AsyncSession = Depends(get_db), category: str = None):
    """Retrieve a random message from a specific category asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool.message).filter(ScheduledMessagePool.category == category))
        messages = result.scalars().all()
        return random.choice(messages) if messages else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve random message: {e}")
        return None

async def add_message_to_pool(db: AsyncSession = Depends(get_db), category: str = None, message: str = None):
    """Add a message to the scheduled message pool asynchronously."""
    try:
        new_message = ScheduledMessagePool(category=category, message=message)
        db.add(new_message)
        await db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to add message to pool: {e}")
        await db.rollback()
        return {"error": "Database error"}

async def delete_message_from_pool(db: AsyncSession = Depends(get_db), message_id: int = None):
    """Remove a message from the pool by ID asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool).filter(ScheduledMessagePool.id == message_id))
        message = result.scalars().first()
        if message:
            await db.delete(message)
            await db.commit()
            return {"success": True}
        return {"error": "Message not found"}
    except Exception as e:
        logger.error(f"❌ Failed to delete message from pool: {e}")
        await db.rollback()
        return {"error": "Database error"}

async def get_messages_from_pool(db: AsyncSession = Depends(get_db), category: str = None):
    """Retrieve all messages from a specific category asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool.id, ScheduledMessagePool.message)
                                  .filter(ScheduledMessagePool.category == category))
        return result.all()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve messages from pool: {e}")
        return []

async def get_categories(db: AsyncSession = Depends(get_db)):
    """Retrieve a list of all unique categories from ScheduledMessagePool asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool.category).distinct())
        categories = result.scalars().all()
        return categories  # Returns a list of unique category names
    except Exception as e:
        logger.error(f"❌ Failed to retrieve categories: {e}")
        return []

async def update_pool_message(message_id: int = None, new_category: str = None, new_message: str = None, db: AsyncSession = Depends(get_db)):
    """Update an existing message in the message pool asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool).filter(ScheduledMessagePool.id == message_id))
        pool_message = result.scalars().first()

        if not pool_message:
            return False

        if new_category is not None:
            pool_message.category = new_category
        pool_message.message = new_message

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update pool message: {e}")
        await db.rollback()
        return False

async def get_scheduled_message_pool(db: AsyncSession = Depends(get_db)):
    """Retrieve all messages from the scheduled message pool asynchronously."""
    try:
        result = await db.execute(select(ScheduledMessagePool.id, ScheduledMessagePool.category, ScheduledMessagePool.message))
        messages = result.mappings().all()
        return [dict(msg) for msg in messages]
    except Exception as e:
        logger.error(f"❌ Failed to retrieve message pool: {e}")
        return []
