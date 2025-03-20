import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from database.crud.todos import save_todo, get_todos, complete_todo

router = APIRouter(prefix="/todo", tags=["ToDos"])

logger = logging.getLogger("uvicorn.error.todo")


@router.post("/")
def create_todo(text: str, twitch_id: int):
    """Create a new ToDo linked to a Twitch user."""
    return save_todo(text=text, twitch_id=twitch_id)


@router.get("/")
def read_todos():
    """Retrieve all ToDos."""
    return get_todos()


@router.get("/status/{filter}")
def read_todos_filtered(filter: str):
    """Retrieve ToDos based on status (pending/completed)."""
    return get_todos(status=filter) if filter else get_todos()


@router.put("/{todo_id}")
def update_todo_status(todo_id: str):
    """Mark a ToDo as completed."""
    return complete_todo(todo_id=todo_id)


@router.delete("/{todo_id}")
def delete_todo(todo_id: str):
    """Delete a ToDo by ID."""
    from database.crud.todos import (
        remove_todo,
    )  # Falls remove_todo() fehlt, implementieren

    return remove_todo(todo_id)


@router.get("/todos", response_class=HTMLResponse)
async def todos_page(status: str = None):
    """Retrieve ToDos as an HTML table."""
    todos = get_todos(status=status)

    rows = ""
    for todo in todos:
        rows += f"""
        <tr class="border-b border-gray-700">
            <td class="px-4 py-2">{todo.get("text")}</td>
            <td class="px-4 py-2">{todo.get("status").capitalize()}</td>
            <td class="px-4 py-2">{todo.get("username", "Unknown")}</td>
            <td class="px-4 py-2 flex space-x-2">
                <button class="bg-blue-500 px-3 py-1 text-white rounded" onclick="triggerButtonAction('show_todo', JSON.parse('{{}}'), '{todo.get('id')}')">👁️</button>
                <button class="bg-yellow-500 px-3 py-1 text-black rounded" onclick="triggerButtonAction('hide_todo', JSON.parse('{{}}'), '{todo.get('id')}')">🙈</button>
                <button class="bg-red-500 px-3 py-1 text-white rounded" onclick="triggerButtonAction('remove_todo', JSON.parse('{{}}'), '{todo.get('id')}')">🗑️</button>
            </td>
        </tr>
        """

    return f"""{rows or '<tr><td colspan="5" class="text-center text-gray-500">No ToDos found.</td></tr>'}"""
