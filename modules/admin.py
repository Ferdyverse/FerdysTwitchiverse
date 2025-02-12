from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modules.db_manager import get_db, save_event, AdminButton
from modules.websocket_handler import broadcast_message
from modules.schemas import AdminButtonCreate
import logging
import json

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

logger = logging.getLogger("uvicorn.error.twitch")

templates = Jinja2Templates(directory="templates")

@router.get("/buttons", response_class=HTMLResponse)
async def get_admin_buttons(request: Request, db: Session = Depends(get_db)):
    """Retrieve all admin panel buttons as an HTML template."""
    buttons = db.query(AdminButton).all()

    # ✅ Ensure valid response even when no buttons exist
    return templates.TemplateResponse("admin_buttons.html", {
        "request": request,
        "buttons": buttons if buttons else []
    })


@router.post("/buttons/add/", response_class=HTMLResponse)
async def add_admin_button(request: Request, db: Session = Depends(get_db)):
    """Add a new button and return updated button list."""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    button_data = json.dumps(body["data"]) if isinstance(body["data"], dict) else "{}"

    new_button = AdminButton(
        label=body["label"],
        action=body["action"],
        data=button_data
    )

    db.add(new_button)
    db.commit()
    db.refresh(new_button)

    buttons = db.query(AdminButton).all()

    # Swap only the button list
    return templates.TemplateResponse("admin_buttons.html", {"request": request, "buttons": buttons})



@router.get("/buttons/edit/{button_id}", response_class=HTMLResponse)
def edit_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Retrieve the edit form for a specific button."""
    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    # Safely decode JSON, fallback to empty dict if invalid
    try:
        button_data = json.loads(button.data) if button.data and button.data.strip() else {}
    except json.JSONDecodeError:
        button_data = {}

    return templates.TemplateResponse("admin_edit_button.html", {
        "request": request,
        "button": button,
        "button_data": json.dumps(button_data, indent=2)  # Pretty JSON
    })


@router.put("/buttons/update/{button_id}")
async def update_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing admin button."""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    # Fetch the button from the DB
    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    # Ensure `data` is a valid JSON string
    try:
        button_data = json.dumps(body["data"]) if isinstance(body["data"], dict) else "{}"
    except json.JSONDecodeError:
        button_data = "{}"

    # Update button fields
    button.label = body["label"]
    button.action = body["action"]
    button.data = button_data  # Store as JSON string

    db.commit()
    db.refresh(button)

    return templates.TemplateResponse("admin_buttons.html", {"request": request, "buttons": db.query(AdminButton).all()})
@router.delete("/buttons/remove/{button_id}", response_class=HTMLResponse)
async def remove_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Remove a button and return updated list."""

    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    db.delete(button)
    db.commit()

    buttons = db.query(AdminButton).all()

    # Swap only the button list
    return templates.TemplateResponse("admin_buttons.html", {"request": request, "buttons": buttons})


@router.post("/trigger-overlay/")
async def trigger_overlay(action: str, data: str = None, db: Session = Depends(get_db)):
    """Trigger an overlay event from the admin panel."""
    if not action:
        raise HTTPException(status_code=400, detail="Missing action type")

    save_event("admin_action", None, f"Triggered overlay: {action} ({data or 'No Data'})", db)

    await broadcast_message({
        "overlay_event": {
            "action": action,
            "data": data if data else None
        }
    })

    return {"status": "success", "message": f"Overlay triggered: {action} with data: {data or 'None'}"}
