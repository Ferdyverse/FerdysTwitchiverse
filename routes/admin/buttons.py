from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import json
import logging
from modules.db_manager import get_db, get_admin_buttons, AdminButton
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("uvicorn.error.admin")

router = APIRouter(prefix="/buttons", tags=["Admin Buttons"])

@router.get("/", response_class=HTMLResponse)
async def get_buttons(request: Request):
    """Retrieve all admin panel buttons."""
    buttons = get_admin_buttons()
    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons or []})

@router.post("/add", response_class=HTMLResponse)
async def add_admin_button(request: Request, db: Session = Depends(get_db)):
    """Add a new button."""
    try:
        body = await request.json()
        label, action, data = body.get("label"), body.get("action"), body.get("data", {})
        if not label or not action:
            raise HTTPException(status_code=400, detail="Label and Action are required.")

        new_button = AdminButton(label=label, action=action, data=json.dumps(data), prompt=body.get("prompt", False))
        db.add(new_button)
        db.commit()

        return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": get_admin_buttons()})

    except Exception as e:
        logger.error(f"❌ Error adding button: {e}")
        raise HTTPException(status_code=500, detail="Failed to add button.")
