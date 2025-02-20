from fastapi import APIRouter, Request, Depends, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging

from modules.schemas import OverlayMessage
from modules import event_handlers
from modules.websocket_handler import broadcast_message
from database.session import get_db
from database.crud.overlay import get_overlay_data
from modules.sequence_runner import execute_sequence, reload_sequences, load_sequences
from modules.event_queue import event_queue  # Ensure this module exists
from modules.heat_api import add_clickable_object, remove_clickable_object, get_clickable_objects
from database.crud.events import save_event  # Importing save_event
from modules.schemas import OverlayMessage

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/overlay", tags=["Overlay"])

logger = logging.getLogger("uvicorn.error.overlay")

@router.get("/", response_class=HTMLResponse)
async def overlay(request: Request):
    """Display the main overlay page for OBS."""
    return templates.TemplateResponse("overlay.html", {"request": request})

@router.get("/solar", response_class=HTMLResponse)
async def solarsystem(request: Request):
    """Display the solar system overlay."""
    return templates.TemplateResponse("solar-system.html", {"request": request})

@router.get("/raid", response_class=HTMLResponse)
async def raiders(request: Request):
    """Display the Raid overlay."""
    return templates.TemplateResponse("raid.html", {"request": request})

@router.post(
    "/send",
    summary="Send data to the overlay",
    description="Accepts data and broadcasts it to all connected WebSocket clients for overlay updates.",
    response_description="Acknowledges the broadcast status."
)
async def send_to_overlay(payload: OverlayMessage = Body(...)):
    """
    Endpoint to send data to the overlay via WebSocket.
    Ensures errors in event processing do not trigger a broadcast.
    """
    all_success = True  # Track success

    try:
        for event_type, event_data in payload.model_dump().items():
            if event_data:  # Only process non-empty events
                success = await event_handlers.handle_event(event_type, event_data, add_clickable_object, remove_clickable_object)
                logger.info(f"🔍 handle_event() returned: {success}")
                if not success:
                    logger.error(f"❌ Event failed: {event_type}")
                    all_success = False  # Mark failure

        # Only broadcast if all events succeeded
        if all_success:
            await broadcast_message(payload.model_dump())
            logger.info(f"📡 Data broadcasted to overlay: {payload.model_dump()}")
            return {"status": "success", "message": "Data sent to overlay"}
        else:
            logger.error("❌ Some events failed, skipping broadcast.")
            return {"status": "error", "message": "One or more events failed. No broadcast sent."}

    except Exception as e:
        logger.error(f"❌ Error in send_to_overlay: {e}")
        return {"status": "error", "message": "Failed to send data"}

@router.get(
    "/data",
    summary="Fetch overlay data",
    description="Retrieves the last follower and subscriber from the database.",
    response_description="Returns the last follower and subscriber."
)
async def fetch_overlay_data(db: Session = Depends(get_db)):
    """
    Endpoint to fetch the most recent follower and subscriber from the database.
    """

    return {
        "last_follower": get_overlay_data("last_follower", db) or "None",
        "last_subscriber": get_overlay_data("last_subscriber", db) or "None",
        "goal_text": get_overlay_data("goal_text", db) or "None",
        "goal_current": get_overlay_data("goal_current", db) or "None",
        "goal_target": get_overlay_data("goal_target", db) or "None"
    }

@router.post("/trigger/")
async def trigger_overlay(request: Request):
    body = await request.json()
    action = body.get("action")
    data = body.get("data", {})

    if not action:
        raise HTTPException(status_code=400, detail="Missing action type")

    ACTION_SEQUENCES = load_sequences()

    if action in ACTION_SEQUENCES:
        await execute_sequence(action, event_queue, data)  # Pass event_queue
    else:
        save_event("overlay_action", None, f"Direct overlay action: {action} with data: {data}")
        await broadcast_message({"overlay_event": {"action": action, "data": data}})

    return {"status": "success", "message": f"Overlay triggered: {action}"}

@router.post("/reload-sequences")
async def reload_sequences_endpoint():
    """Manually reload sequences from YAML file."""
    await reload_sequences()
    return {"status": "success", "message": "Sequences reloaded!"}

@router.get("/clickable-objects")
async def list_clickable_objects():
    """Retrieve all currently defined clickable objects."""
    return get_clickable_objects()
