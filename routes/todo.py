import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.crud.todos import (
    save_todo,
    get_todos,
    complete_todo,
    delete_todo as remove_todo,
)

router = APIRouter(prefix="/todo", tags=["ToDos"])
logger = logging.getLogger("uvicorn.error.todo")


@router.post("/")
async def create_todo(text: str, twitch_id: int, db: AsyncSession = Depends(get_db)):
    """Create a new ToDo linked to a Twitch user."""
    try:
        todo = await save_todo(db=db, text=text, twitch_id=twitch_id)
        logger.info(f"✅ ToDo created: {todo}")
        return todo
    except Exception as e:
        logger.error(f"❌ Error creating ToDo: {e}")
        raise HTTPException(status_code=500, detail="Failed to create ToDo.")


@router.get("/")
async def read_todos(db: AsyncSession = Depends(get_db)):
    """Retrieve all ToDos."""
    try:
        todos = await get_todos(db=db)
        return todos if todos else []
    except Exception as e:
        logger.error(f"❌ Error retrieving ToDos: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ToDos.")


@router.get("/status/{filter}")
async def read_todos_filtered(filter: str, db: AsyncSession = Depends(get_db)):
    """Retrieve ToDos based on status (pending/completed)."""
    try:
        return await get_todos(db=db, status=filter) if filter else await get_todos(db=db)
    except Exception as e:
        logger.error(f"❌ Error filtering ToDos by '{filter}': {e}")
        raise HTTPException(status_code=500, detail="Failed to filter ToDos.")


@router.put("/{todo_id}")
async def update_todo_status(todo_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a ToDo as completed."""
    try:
        result = await complete_todo(db=db, todo_id=todo_id)
        logger.info(f"✅ ToDo completed: ID {todo_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error completing ToDo ID {todo_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete ToDo.")


@router.delete("/{todo_id}")
async def delete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a ToDo by ID."""
    try:
        success = await remove_todo(db=db, todo_id=todo_id)
        if success:
            logger.info(f"🗑️ ToDo deleted: ID {todo_id}")
            return {"status": "success", "message": f"ToDo ID {todo_id} deleted."}
        else:
            raise HTTPException(status_code=404, detail="ToDo not found.")
    except Exception as e:
        logger.error(f"❌ Error deleting ToDo ID {todo_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete ToDo.")


@router.get("/todos", response_class=HTMLResponse)
async def todos_page(status: str = None, db: AsyncSession = Depends(get_db)):
    """Retrieve ToDos as an HTML table."""
    try:
        todos = await get_todos(db=db, status=status)
        if not todos:
            return '<tr><td colspan="5" class="text-center text-gray-500">No ToDos found.</td></tr>'

        rows = "".join([
            f"""
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
            """ for todo in todos
        ])
        return HTMLResponse(content=rows)

    except Exception as e:
        logger.error(f"❌ Error generating ToDo HTML: {e}")
        return HTMLResponse(content='<tr><td colspan="5" class="text-center text-red-500">Error loading ToDos.</td></tr>')
