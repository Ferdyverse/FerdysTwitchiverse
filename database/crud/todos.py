from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.base import Todo, Viewer
import datetime

async def get_todos(db: AsyncSession, status=None):
    """Retrieve all ToDos or filter by 'pending'/'completed' asynchronously."""
    try:
        query = select(
            Todo.id, Todo.text, Todo.created_at, Todo.status,
            Viewer.display_name.label("username"),
            Todo.twitch_id
        ).join(Viewer, Todo.twitch_id == Viewer.twitch_id)

        if status in ["pending", "completed"]:
            query = query.filter(Todo.status == status)

        result = await db.execute(query.order_by(Todo.id.asc()))
        return [dict(todo) for todo in result.mappings().all()]
    except Exception as e:
        print(f"❌ Error retrieving ToDos: {e}")
        return []

async def save_todo(text: str, twitch_id: int, db: AsyncSession):
    """Save a new ToDo asynchronously."""
    try:
        todo = Todo(text=text, twitch_id=twitch_id, status="pending", created_at=datetime.datetime.utcnow())
        db.add(todo)
        await db.commit()
        await db.refresh(todo)
        return todo
    except Exception as e:
        print(f"❌ Error saving ToDo: {e}")
        await db.rollback()
        return None

async def complete_todo(todo_id: int, db: AsyncSession):
    """Mark a ToDo as completed asynchronously."""
    try:
        result = await db.execute(select(Todo).filter(Todo.id == todo_id))
        todo = result.scalars().first()

        if not todo:
            return None

        todo.status = "completed"
        await db.commit()
        await db.refresh(todo)
        return todo
    except Exception as e:
        print(f"❌ Failed to update ToDo: {e}")
        await db.rollback()
        return None

async def delete_todo(todo_id: int, db: AsyncSession):
    """Delete a ToDo asynchronously."""
    try:
        result = await db.execute(select(Todo).filter(Todo.id == todo_id))
        todo = result.scalars().first()

        if not todo:
            return None

        await db.delete(todo)
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Failed to delete ToDo: {e}")
        await db.rollback()
        return None
