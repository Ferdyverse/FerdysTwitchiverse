from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modules.db_manager import get_db, save_event, AdminButton
from modules.websocket_handler import broadcast_message
from modules.schemas import AdminButtonCreate
import logging

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

logger = logging.getLogger("uvicorn.error.twitch")

templates = Jinja2Templates(directory="templates")

@router.get("/buttons", response_class=HTMLResponse)
def get_admin_buttons(request: Request, db: Session = Depends(get_db)):
    """Retrieve all admin panel buttons as an HTML template."""
    buttons = db.query(AdminButton).all()
    return templates.TemplateResponse("admin_buttons.html", {"request": request, "buttons": buttons})

@router.post("/buttons/add/")
def add_admin_button(button: AdminButtonCreate, db: Session = Depends(get_db)):
    """Add a new button to the admin panel."""
    new_button = AdminButton(label=button.label, action=button.action)
    db.add(new_button)
    db.commit()
    db.refresh(new_button)
    return {"status": "success", "message": "Button added!", "button": new_button}

@router.delete("/buttons/remove/{button_id}")
def remove_admin_button(button_id: int, db: Session = Depends(get_db)):
    """Remove a button from the admin panel."""
    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    db.delete(button)
    db.commit()
    return {"status": "success", "message": "Button removed!"}

@router.post("/trigger-overlay/")
async def trigger_overlay(action: str, data: dict, db: Session = Depends(get_db)):
    """Trigger an overlay event from the admin panel."""
    if not action:
        raise HTTPException(status_code=400, detail="Missing action type")

    save_event("admin_action", None, f"Triggered overlay: {action}", db)
    await broadcast_message({"overlay_event": {"action": action, "data": data}})

    return {"status": "success", "message": f"Overlay triggered: {action}"}
