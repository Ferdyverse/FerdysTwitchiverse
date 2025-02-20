from sqlalchemy.orm import Session
from database.session import SessionLocal
from database.base import Todo, Viewer
import datetime

def get_todos(status=None):
    """Retrieve all ToDos or filter by 'pending'/'completed', including viewer info."""
    db = SessionLocal()
    try:
        query = db.query(
            Todo.id, Todo.text, Todo.created_at, Todo.status,
            Viewer.display_name.label("username"),
            Todo.twitch_id
        ).join(Viewer, Todo.twitch_id == Viewer.twitch_id)

        if status in ["pending", "completed"]:
            query = query.filter(Todo.status == status)

        return [dict(todo._mapping) for todo in query.order_by(Todo.id.asc()).all()]
    except Exception as e:
        print(f"❌ Error retrieving ToDos: {e}")
        return []
    finally:
        db.close()

def save_todo(text: str, twitch_id: int):
    """Save a new ToDo."""
    db = SessionLocal()
    try:
        todo = Todo(text=text, twitch_id=twitch_id, status="pending", created_at=datetime.datetime.utcnow())
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo
    except Exception as e:
        print(f"❌ Error saving ToDo: {e}")
        return None
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
        print(f"❌ Failed to update ToDo: {e}")
    finally:
        db.close()
