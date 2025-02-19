import logging
from fastapi import APIRouter
from modules.db_manager import save_todo, get_todos, complete_todo

router = APIRouter(prefix="/todo", tags=["ToDos"])

logger = logging.getLogger("uvicorn.error.todo")

@router.post("/")
def create_todo(text: str, twitch_id: int):
    """Create a new ToDo linked to a Twitch user."""
    return save_todo(text, twitch_id)

@router.get("/")
def read_todos():
    """Retrieve all ToDos."""
    todos = get_todos()
    return todos

@router.put("/{todo_id}")
def update_todo_status(todo_id: int):
    """Mark a ToDo as completed."""
    return complete_todo(todo_id)

@router.delete("/{todo_id}")
def delete_todo(todo_id: int):
    """Delete a ToDo by ID."""
    #remove_todo(todo_id)
    #return {"message": "ToDo deleted"}
    return False
