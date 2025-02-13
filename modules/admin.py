from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modules.db_manager import get_db, save_event, AdminButton, ChatMessage, save_viewer
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import get_sequence_names
import logging
import json
import config

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

    sequence_names = get_sequence_names()
    return templates.TemplateResponse("admin_edit_button.html", {
        "request": request,
        "button": button,
        "sequence_names": sequence_names,
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

@router.post("/update-viewer/{user_id}")
async def update_viewer(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Fetch latest user info and update the viewer database."""

    twitch_api = request.app.state.twitch_api

    try:
        user_info = await twitch_api.get_user_info(user_id=user_id)

        if not user_info:
            raise HTTPException(status_code=404, detail="User not found in Twitch API")

        # Update viewer in DB
        save_viewer(
            twitch_id=user_id,
            login=user_info["login"],
            display_name=user_info["display_name"],
            account_type=user_info["type"],
            broadcaster_type=user_info["broadcaster_type"],
            profile_image_url=user_info["profile_image_url"],
            account_age="",
            follower_date=None,
            subscriber_date=None,
            color=user_info.get("color"),
            badges=",".join(user_info.get("badges", [])),
            db=db
        )

        # Broadcast update
        await broadcast_message({"admin_alert": {"type": "viewer_update", "user_id": user_id, "message": "Viewer info updated"}})

        return {"status": "success", "message": "Viewer information updated"}

    except Exception as e:
        logger.error(f"❌ Failed to update viewer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update viewer: {str(e)}")

@router.delete("/delete-message/{message_id}", response_class=HTMLResponse)
async def delete_chat_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a chat message from Twitch and the local database."""

    twitch_api = request.app.state.twitch_api  # Access `twitch_api` from `app.state`

    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    user_id = message.viewer_id  # Get Twitch user ID

    try:
        # Delete the message from Twitch chat
        await twitch_api.twitch.delete_chat_message(config.TWITCH_CHANNEL_ID, user_id, message_id)
        logger.info(f"🗑️ Deleted message {message_id} from Twitch chat.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete Twitch chat message: {str(e)}")

    # Delete from local DB
    db.delete(message)
    db.commit()

    # Refresh the chat UI
    await broadcast_message({"admin_alert": {"type": "chat_update", "message": "Message deleted"}})

    return await get_chat_messages(db)
