import random
import logging
from database.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.scheduled_messages")


def get_random_message_from_category(category: str):
    """Retrieve a random message from a specific category in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        messages = [
            db[doc]
            for doc in db
            if db[doc].get("type") == "scheduled_message"
            and db[doc].get("category") == category
        ]

        return random.choice(messages)["message"] if messages else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve random message: {e}")
        return None


def add_message_to_pool(category: str, message: str):
    """Add a message to the scheduled message pool in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        new_message = {
            "_id": f"message_{random.randint(10000, 99999)}",
            "type": "scheduled_message",
            "category": category,
            "message": message,
        }

        db.save(new_message)
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to add message to pool: {e}")
        return {"error": "Database error"}


def delete_message_from_pool(message_id: str):
    """Remove a message from the pool by ID in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        if message_id in db:
            db.delete(db[message_id])
            return {"success": True}

        return {"error": "Message not found"}
    except Exception as e:
        logger.error(f"❌ Failed to delete message from pool: {e}")
        return {"error": "Database error"}


def get_messages_from_pool(category: str):
    """Retrieve all messages from a specific category in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        return [
            {"id": doc, "message": db[doc]["message"]}
            for doc in db
            if db[doc].get("type") == "scheduled_message"
            and db[doc].get("category") == category
        ]
    except Exception as e:
        logger.error(f"❌ Failed to retrieve messages from pool: {e}")
        return []


def get_categories():
    """Retrieve a list of all unique categories from ScheduledMessagePool in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        categories = set(
            db[doc]["category"]
            for doc in db
            if db[doc].get("type") == "scheduled_message"
        )

        return list(categories)
    except Exception as e:
        logger.error(f"❌ Failed to retrieve categories: {e}")
        return []


def update_pool_message(
    message_id: str, new_category: str = None, new_message: str = None
):
    """Update an existing message in the CouchDB message pool, including category."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        if message_id not in db:
            return False

        pool_message = db[message_id]

        if new_category:
            pool_message["category"] = new_category
        if new_message:
            pool_message["message"] = new_message

        db.save(pool_message)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update pool message: {e}")
        return False


def get_scheduled_message_pool():
    """Retrieve all messages from the scheduled message pool in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_messages")  # ✅ Korrekte DB!

        messages = [
            {"id": doc, "category": db[doc]["category"], "message": db[doc]["message"]}
            for doc in db
            if db[doc].get("type") == "scheduled_message"
        ]

        return messages
    except Exception as e:
        logger.error(f"❌ Failed to retrieve message pool: {e}")
        return []
