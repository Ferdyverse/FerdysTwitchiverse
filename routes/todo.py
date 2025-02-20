import logging
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.todos import save_todo, get_todos, complete_todo

router = APIRouter(prefix="/todo", tags=["ToDos"])

logger = logging.getLogger("uvicorn.error.todo")

@router.post("/")
def create_todo(text: str, twitch_id: int, db: Session = Depends(get_db)):
    """Create a new ToDo linked to a Twitch user."""
    return save_todo(db=db, text=text, twitch_id=twitch_id)

@router.get("/")
def read_todos(db: Session = Depends(get_db)):
    """Retrieve all ToDos."""
    return get_todos(db=db)

@router.get("/status/{filter}")
def read_todos_filtered(filter: str, db: Session = Depends(get_db)):
    """Retrieve ToDos based on status (pending/completed)."""
    return get_todos(db=db, status=filter) if filter else get_todos(db=db)

@router.put("/{todo_id}")
def update_todo_status(todo_id: int, db: Session = Depends(get_db)):
    """Mark a ToDo as completed."""
    return complete_todo(db=db, todo_id=todo_id)

@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """Delete a ToDo by ID."""
    # Implement the remove function in CRUD
    return {"error": "Function not implemented"}

@router.get("/todos", response_class=HTMLResponse)
async def todos_page(status: str = None, db: Session = Depends(get_db)):
    """Retrieve ToDos as an HTML table."""
    todos = get_todos(db=db, status=status)

    rows = ""
    for todo in todos:
        rows += f"""
        <tr class="border-b border-gray-700">
            <td class="px-4 py-2">{todo["id"]}</td>
            <td class="px-4 py-2">{todo["text"]}</td>
            <td class="px-4 py-2">{todo["status"].capitalize()}</td>
            <td class="px-4 py-2">{todo["username"]}</td>
            <td class="px-4 py-2 flex space-x-2">
                <button class="bg-blue-500 px-3 py-1 text-white rounded" onclick="triggerButtonAction('show_todo', JSON.parse('{{}}'), {todo['id']})">👁️</button>
                <button class="bg-yellow-500 px-3 py-1 text-black rounded" onclick="triggerButtonAction('hide_todo', JSON.parse('{{}}'), {todo['id']})">🙈</button>
                <button class="bg-red-500 px-3 py-1 text-white rounded" onclick="triggerButtonAction('remove_todo', JSON.parse('{{}}'), {todo['id']})">🗑️</button>
            </td>
        </tr>
        """

    return f"""{rows or '<tr><td colspan="5" class="text-center text-gray-500">No ToDos found.</td></tr>'}"""
