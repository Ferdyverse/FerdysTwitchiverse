import datetime
import logging
import uuid
from database.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.todos")


def get_todos(status=None):
    """Retrieve all ToDos or filter by 'pending'/'completed' from CouchDB."""
    try:
        db = couchdb_client.get_db("todos")

        todos = [
            {
                "id": doc,
                "text": db[doc]["text"],
                "created_at": db[doc]["created_at"],
                "status": db[doc]["status"],
                "username": db[doc].get("username", "Unknown"),
                "twitch_id": db[doc]["twitch_id"]
            }
            for doc in db
            if db[doc].get("type") == "todo" and (status is None or db[doc]["status"] == status)
        ]

        return sorted(todos, key=lambda x: x["created_at"])
    except Exception as e:
        logger.error(f"❌ Failed to retrieve ToDos: {e}")
        return []


def save_todo(text: str, twitch_id: int, username: str):
    """Save a new ToDo in CouchDB."""
    try:
        db = couchdb_client.get_db("todos")

        todo = {
            "_id": f"todo_{uuid.uuid4().hex}",
            "type": "todo",
            "text": text,
            "twitch_id": twitch_id,
            "username": username,
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        db.save(todo)
        return todo
    except Exception as e:
        logger.error(f"❌ Error saving ToDo: {e}")
        return None


def complete_todo(todo_id: str):
    """Mark a ToDo as completed in CouchDB."""
    try:
        db = couchdb_client.get_db("todos")

        if todo_id not in db:
            return None

        todo = db[todo_id]
        todo["status"] = "completed"

        db.save(todo)
        return todo
    except Exception as e:
        logger.error(f"❌ Failed to update ToDo: {e}")
        return None


def delete_todo(todo_id: str):
    """Delete a ToDo from CouchDB."""
    try:
        db = couchdb_client.get_db("todos")

        if todo_id in db:
            db.delete(db[todo_id])
            return {"success": True}

        return {"error": "ToDo not found"}
    except Exception as e:
        logger.error(f"❌ Failed to delete ToDo: {e}")
        return {"error": "Database error"}
