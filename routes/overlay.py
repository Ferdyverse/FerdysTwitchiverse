from fastapi import APIRouter, Request, Depends, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from modules.schemas import OverlayMessage
from modules import event_handlers
from modules.websocket_handler import broadcast_message
from database.session import get_db
from database.crud.overlay import get_overlay_data
from modules.sequence_runner import execute_sequence, reload_sequences, load_sequences
from modules.heat_api import add_clickable_object, remove_clickable_object, get_clickable_objects
from database.crud.events import save_event

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/overlay", tags=["Overlay"])
logger = logging.getLogger("uvicorn.error.overlay")


### 🔹 Overlay Pages ###
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


### 🔹 Sending Data to Overlay ###
@router.post("/send", summary="Send data to the overlay")
async def send_to_overlay(payload: OverlayMessage = Body(...)):
    """
    Sends data to the overlay via WebSocket and ensures event processing is error-free.
    """
    try:
        all_success = True  # Track success

        for event_type, event_data in payload.model_dump().items():
            if event_data:  # Process only non-empty events
                success = await event_handlers.handle_event(event_type, event_data, add_clickable_object, remove_clickable_object)
                if not success:
                    logger.error(f"❌ Event processing failed: {event_type}")
                    all_success = False

        if all_success:
            await broadcast_message(payload.model_dump())
            return {"status": "success", "message": "Data sent to overlay"}

        return {"status": "error", "message": "One or more events failed. No broadcast sent."}

    except Exception as e:
        logger.exception("❌ Error in send_to_overlay")
        return {"status": "error", "message": "Failed to send data"}


### 🔹 Fetch Overlay Data ###
@router.get("/data", summary="Fetch overlay data")
async def fetch_overlay_data(db: AsyncSession = Depends(get_db)):
    """Retrieves overlay state from the database asynchronously."""
    try:
        return {
            "last_follower": await get_overlay_data("last_follower", db) or "None",
            "last_subscriber": await get_overlay_data("last_subscriber", db) or "None",
            "goal_text": await get_overlay_data("goal_text", db) or "None",
            "goal_current": await get_overlay_data("goal_current", db) or "None",
            "goal_target": await get_overlay_data("goal_target", db) or "None",
        }
    except Exception as e:
        logger.error(f"❌ Error fetching overlay data: {e}")
        return {"status": "error", "message": "Failed to retrieve overlay data"}


### 🔹 Trigger Overlay Actions ###
@router.post("/trigger/")
async def trigger_overlay(request: Request):
    """
    Triggers an overlay event via WebSocket or executes a stored sequence.
    """
    try:
        body = await request.json()
        action = body.get("action")
        data = body.get("data", {})

        if not action:
            raise HTTPException(status_code=400, detail="Missing action type")

        event_queue = request.app.state.event_queue
        ACTION_SEQUENCES = load_sequences()

        if action in ACTION_SEQUENCES:
            await execute_sequence(action, event_queue, data)
            return {"status": "success", "message": f"Sequence triggered: {action}"}

        await save_event("overlay_action", None, f"Direct overlay action: {action} with data: {data}", db=await get_db())
        await broadcast_message({"overlay_event": {"action": action, "data": data}})

        return {"status": "success", "message": f"Overlay action triggered: {action}"}

    except Exception as e:
        logger.exception(f"❌ Error triggering overlay: {e}")
        return {"status": "error", "message": "Failed to trigger overlay"}


### 🔹 Reload Sequences ###
@router.post("/reload-sequences")
async def reload_sequences_endpoint():
    """Manually reload sequences from YAML file."""
    try:
        await reload_sequences()
        return {"status": "success", "message": "Sequences reloaded!"}
    except Exception as e:
        logger.error(f"❌ Error reloading sequences: {e}")
        return {"status": "error", "message": "Failed to reload sequences"}


### 🔹 Clickable Objects ###
@router.get("/clickable-objects")
async def list_clickable_objects():
    """Retrieve all currently defined clickable objects."""
    try:
        return get_clickable_objects()
    except Exception as e:
        logger.error(f"❌ Error retrieving clickable objects: {e}")
        return {"status": "error", "message": "Failed to retrieve clickable objects"}
