from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modules.db_manager import (
    get_db, get_scheduled_messages, add_scheduled_message, remove_scheduled_message,
    get_categories, update_pool_message, get_scheduled_message_pool, add_message_to_pool,
    delete_message_from_pool, update_scheduled_message
)
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/scheduled", tags=["Scheduled Messages"])

@router.get("/messages", response_class=HTMLResponse)
async def scheduled_messages(request: Request):
    """Retrieve scheduled messages."""
    messages = get_scheduled_messages()
    return templates.TemplateResponse("includes/admin_scheduled_messages.html", {"request": request, "messages": messages})

@router.post("/messages/add")
async def create_or_update_scheduled_message(data: dict = Body(...)):
    """Add or update a scheduled message."""
    message_id, message, interval, category = data.get("id"), data.get("message"), data.get("interval"), data.get("category")

    if not interval or (not message and not category):
        raise HTTPException(status_code=400, detail="Provide a message or category with an interval.")

    if message_id:
        return {"success": update_scheduled_message(message_id, message, interval, category)}

    add_scheduled_message(message=message, category=category, interval=interval)
    return {"success": True}

@router.delete("/messages/{message_id}")
async def delete_scheduled_message(message_id: int):
    remove_scheduled_message(message_id)
    return {"success": True}

@router.get("/pools", response_class=HTMLResponse)
async def scheduled_message_pool(request: Request):
    """Retrieve message pools."""
    messages = get_scheduled_message_pool()
    return templates.TemplateResponse("includes/admin_message_pool.html", {"request": request, "messages": messages})
