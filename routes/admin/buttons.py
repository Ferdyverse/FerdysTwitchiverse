from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.admin_buttons import get_admin_buttons, add_admin_button, update_admin_button, remove_admin_button, reorder_admin_buttons

templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("uvicorn.error.admin")

router = APIRouter(prefix="/buttons", tags=["Admin Buttons"])

@router.get("/", response_class=HTMLResponse)
async def get_buttons(request: Request, db: Session = Depends(get_db)):
    """Retrieve all admin panel buttons."""
    buttons = get_admin_buttons(db)
    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons or []})

@router.post("/add/", response_class=HTMLResponse)
async def add_admin_button(request: Request, db: Session = Depends(get_db)):
    """Add a new button and return updated button list."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    buttons = add_admin_button(db, body["label"], body["action"], body["data"], body.get("prompt", False))

    if buttons is None:
        raise HTTPException(status_code=500, detail="Failed to add button")

    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons})


@router.put("/update/{button_id}")
async def update_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing admin button."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    buttons = update_admin_button(db, button_id, body["label"], body["action"], body["data"], body.get("prompt", False))

    if buttons is None:
        raise HTTPException(status_code=404, detail="Button not found or update failed")

    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons})


@router.delete("/remove/{button_id}", response_class=HTMLResponse)
async def remove_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Remove a button and return updated list."""
    buttons = remove_admin_button(button_id, db)

    if buttons is None:
        raise HTTPException(status_code=404, detail="Button not found")

    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons})


@router.put("/reorder")
def reorder_buttons(updated_buttons: list[dict], db: Session = Depends(get_db)):
    """Update the order of admin buttons."""
    success = reorder_admin_buttons(updated_buttons, db)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update button order")

    return {"message": "Button order updated"}
