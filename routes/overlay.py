from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

from modules.schemas import OverlayMessage
from modules import event_handlers
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence, reload_sequences, load_sequences
from modules.heat_api import add_clickable_object, remove_clickable_object, get_clickable_objects
from database.crud.overlay import get_overlay_data, save_overlay_data
from database.crud.events import save_event

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/overlay", tags=["Overlay"])

logger = logging.getLogger("uvicorn.error.overlay")


### Overlay Pages ###
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


### Sending Data to Overlay ###
@router.post("/send", summary="Send data to the overlay")
async def send_to_overlay(payload: OverlayMessage = Body(...)):
    """
    Sends data to the overlay via WebSocket, ensuring that event processing is error-free.
    """
    try:
        all_success = True  # Track success

        for event_type, event_data in payload.model_dump().items():
            if event_data:  # Process only non-empty events
                success = await event_handlers.handle_event(event_type, event_data, add_clickable_object, remove_clickable_object)
                logger.info(f"🔍 handle_event() returned: {success}")
                if not success:
                    logger.error(f"❌ Event failed: {event_type}")
                    all_success = False  # Mark failure

        # Broadcast only if all events succeeded
        if all_success:
            await broadcast_message(payload.model_dump())
            logger.info(f"📡 Data broadcasted to overlay: {payload.model_dump()}")
            return {"status": "success", "message": "Data sent to overlay"}

        logger.error("❌ Some events failed, skipping broadcast.")
        return {"status": "error", "message": "One or more events failed. No broadcast sent."}

    except Exception as e:
        logger.exception("❌ Error in send_to_overlay")
        return {"status": "error", "message": "Failed to send data"}


### Fetch Overlay Data ###
@router.get("/data", summary="Fetch overlay data")
async def fetch_overlay_data():
    """Retrieves the last follower and subscriber from CouchDB."""
    return {
        "last_follower": get_overlay_data("last_follower") or "None",
        "last_subscriber": get_overlay_data("last_subscriber") or "None",
        "goal_text": get_overlay_data("goal_text") or "None",
        "goal_current": get_overlay_data("goal_current") or "None",
        "goal_target": get_overlay_data("goal_target") or "None"
    }

@router.post("/data")
async def set_overlay_data(request: Request):
    """Set overlay data"""
    try:
        body = await request.json()
        key = body.get("key")
        value = body.get("value")
        save_overlay_data(key, value)
    except Exception as e:
        logger.exception(f"❌ Error set overlay-data: {e}")

### Trigger Overlay Actions ###
@router.post("/trigger/")
async def trigger_overlay(request: Request):
    """
    Triggers an overlay event via WebSocket or executes a stored sequence.
    """
    body = await request.json()
    action = body.get("action")
    data = body.get("data", {})

    if not action:
        raise HTTPException(status_code=400, detail="Missing action type")

    # Retrieve the global event queue from app.state
    event_queue = request.app.state.event_queue

    try:
        ACTION_SEQUENCES = load_sequences()

        if action in ACTION_SEQUENCES:
            # Pass event queue from `app.state`
            await execute_sequence(action, event_queue, data)
        else:
            save_event("overlay_action", None, f"Direct overlay action: {action} with data: {data}")
            await broadcast_message({"overlay_event": {"action": action, "data": data}})

        return {"status": "success", "message": f"Overlay triggered: {action}"}

    except Exception as e:
        logger.exception(f"❌ Error triggering overlay: {e}")
        return {"status": "error", "message": "Failed to trigger overlay"}


### Reload Sequences ###
@router.post("/reload-sequences")
async def reload_sequences_endpoint():
    """Manually reload sequences from YAML file."""
    await reload_sequences()
    return {"status": "success", "message": "Sequences reloaded!"}


### Clickable Objects ###
@router.get("/clickable-objects")
async def list_clickable_objects():
    """Retrieve all currently defined clickable objects."""
    return get_clickable_objects()
