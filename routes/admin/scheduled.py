from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.scheduled_messages import (
    get_scheduled_messages, add_scheduled_message, remove_scheduled_message,
    get_scheduled_message_pool, add_message_to_pool, delete_message_from_pool,
    update_scheduled_message, update_pool_message
)
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/scheduled", tags=["Scheduled Messages"])

@router.get("/messages", response_class=HTMLResponse)
async def scheduled_messages(request: Request, db: Session = Depends(get_db)):
    messages = get_scheduled_messages(db)
    return templates.TemplateResponse("includes/admin_scheduled_messages.html", {
        "request": request,
        "messages": messages
    })

@router.post("/messages/add", response_model=dict)
async def create_or_update_scheduled_message(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """HTMX endpoint to add or update a scheduled message."""
    message_id = data.get("id")  # Check if it's an existing message
    message = data.get("message", "")
    interval = data.get("interval")
    category = data.get("category") if data.get("category") else None

    if not interval or (not message and not category):
        return {"error": "You must provide either a message or a category, and an interval."}

    if message_id:
        success = update_scheduled_message(message_id, message, interval, category, db)
        return {"success": success}

    add_scheduled_message(category=category, interval=interval, db=db)
    return {"success": True}

# ✏️ Edit Scheduled Message
@router.post("/messages/edit/{message_id}")
async def edit_scheduled_message(
    message_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Edit a scheduled message."""
    new_message = data.get("message", "")
    new_interval = data.get("interval")
    new_category = data.get("category") if data.get("category") else None

    if not new_interval or (not new_message and not new_category):
        return {"error": "You must provide either a message or a category, and an interval."}

    success = update_scheduled_message(message_id, new_message, new_interval, new_category, db)
    return {"success": success}

# Delete Scheduled Message
@router.delete("/messages/{message_id}")
async def delete_scheduled_message(message_id: int, db: Session = Depends(get_db)):
    remove_scheduled_message(message_id, db)
    return {"success": True}

# GET Message Pool List
@router.get("/messages/pool", response_class=HTMLResponse)
async def scheduled_message_pool(request: Request, db: Session = Depends(get_db)):
    messages = get_scheduled_message_pool(db)
    return templates.TemplateResponse("includes/admin_message_pool.html", {
        "request": request,
        "messages": messages
    })

# Add Message to Pool
@router.post("/pool/add")
async def create_pool_message(data: dict = Body(...), db: Session = Depends(get_db)):
    category = data.get("category")
    message = data.get("message")

    if not message:
        return {"error": "Message is required."}

    add_message_to_pool(category, message, db)
    return {"success": True}

@router.post("/pool/edit/{message_id}")
async def edit_pool_message(
    message_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Update a message in the scheduled message pool."""
    new_category = data.get("category")
    new_message = data.get("message")

    if not new_message:
        return {"error": "Message cannot be empty."}

    success = update_pool_message(message_id, new_category, new_message, db)

    if success:
        return {"success": True}
    else:
        return {"error": "Failed to update message or category."}

@router.delete("/pool/{message_id}")
async def remove_pool_message(message_id: int, db: Session = Depends(get_db)):
    delete_message_from_pool(message_id, db)
    return {"success": True}
