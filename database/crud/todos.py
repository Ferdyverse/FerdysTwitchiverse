from sqlalchemy.orm import Session
from fastapi import Depends
from database.session import get_db
from database.base import Todo, Viewer
import datetime

def get_todos(status=None, db: Session = Depends(get_db)):
    """Retrieve all ToDos or filter by 'pending'/'completed'."""
    query = db.query(
        Todo.id, Todo.text, Todo.created_at, Todo.status,
        Viewer.display_name.label("username"),
        Todo.twitch_id
    ).join(Viewer, Todo.twitch_id == Viewer.twitch_id)

    if status in ["pending", "completed"]:
        query = query.filter(Todo.status == status)

    return [dict(todo._mapping) for todo in query.order_by(Todo.id.asc()).all()]

def save_todo(text: str, twitch_id: int, db: Session = Depends(get_db)):
    """Save a new ToDo."""
    try:
        todo = Todo(text=text, twitch_id=twitch_id, status="pending", created_at=datetime.datetime.utcnow())
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo
    except Exception as e:
        print(f"❌ Error saving ToDo: {e}")
        db.rollback()
        return None

def complete_todo(todo_id: int, db: Session = Depends(get_db)):
    """Mark a ToDo as completed."""
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not todo:
        return None

    try:
        todo.status = "completed"
        db.commit()
        db.refresh(todo)
        return todo
    except Exception as e:
        print(f"❌ Failed to update ToDo: {e}")
        db.rollback()
