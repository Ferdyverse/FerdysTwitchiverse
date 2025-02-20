import logging
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from database.crud.todos import save_todo, get_todos, complete_todo

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

# ToDos as json objects
@router.get("/status/{filter}")
def read_todos_filtered(filter: str):
    """Retrieve all ToDos."""
    if filter != "":
        todos = get_todos(filter)
    else:
        todos = todos = get_todos()
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

@router.get("/todos", response_class=HTMLResponse)
async def todos_page(status: str = None):
    todos = get_todos(status)

    # Generate table rows dynamically
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
