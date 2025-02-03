#!/usr/bin/env python3

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi import WebSocket, WebSocketDisconnect, Body

# Other required imports
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Any, List
import asyncio
import os

# Own modules
from modules.printer_manager import PrinterManager
from modules.schemas import PrintRequest, OverlayMessage, ClickData, ClickableObject
from modules.db_manager import init_db, get_data, get_planets
from modules.heat_api import HeatAPIClient, update_clickable_objects, CLICKABLE_OBJECTS
from modules.firebot_api import FirebotAPI
from modules import event_handlers
import config

# ✅ ANSI escape codes for colors
LOG_COLORS = {
    "DEBUG": "\033[94m",    # Blue
    "INFO": "\033[92m",     # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",    # Red
    "CRITICAL": "\033[91;1m",  # Bold Red
    "RESET": "\033[0m",     # Reset color
}

class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels."""
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, LOG_COLORS["RESET"])
        log_message = super().format(record)
        return f"{log_color}{log_message}{LOG_COLORS['RESET']}"

DISABLE_HEAT_API = os.getenv("DISABLE_HEAT_API", "false").lower() == "true"
DISABLE_FIREBOT = os.getenv("DISABLE_FIREBOT", "false").lower() == "true"
DISABLE_PRINTER = os.getenv("DISABLE_PRINTER", "false").lower() == "true"

# ✅ Configure the logger
logger = logging.getLogger("uvicorn.error")

# ✅ Apply custom format with colors
formatter = ColorFormatter(
    "%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    datefmt=config.APP_LOG_TIME_FORMAT
)

# ✅ Apply format to all Uvicorn handlers
for handler in logging.getLogger("uvicorn").handlers:
    handler.setFormatter(formatter)

# Instantiate the PrinterManager
printer_manager = PrinterManager()

# Heat API
heat_api_client: HeatAPIClient = None

# ✅ Initialize Firebot API Client
firebot = FirebotAPI(config.FIREBOT_API_URL)

templates = Jinja2Templates(directory="templates")

# Keep track of connected clients
connected_clients = []
clicks: List[ClickData] = []

# ✅ Create an async queue for event sharing
event_queue = asyncio.Queue()

# Required for Startup and Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event manager for the FastAPI application.
    Initializes the database and printer manager on startup and shuts them down on exit.
    """
    logger.info("Initializing modules")
    try:
        init_db()
        asyncio.create_task(process_queue())  # Run in background

        if not DISABLE_PRINTER:
            printer_manager.initialize()
        else:
            logger.info("🚫 Printer is disabled.")

        if not DISABLE_HEAT_API:
            global heat_api_client
            heat_api_client = HeatAPIClient(config.TWITCH_CHANNEL_ID, event_queue)
            heat_api_client.start()
            logger.info("🔥 Heat API started successfully")
        else:
            logger.info("🚫 Heat API is disabled.")

        if not DISABLE_FIREBOT:
            global firebot
            firebot = FirebotAPI(config.FIREBOT_API_URL)
            logger.info("🔥 Firebot API started successfully")
        else:
            logger.info("🚫 Firebot API is disabled.")

        yield  # The app is running
    except Exception as e:
        logger.error(f"Error during lifespan: {e}")
        yield
    finally:
        logger.info("Shutting down modules")
        if not DISABLE_PRINTER:
            printer_manager.shutdown()

        if not DISABLE_HEAT_API and heat_api_client:
            heat_api_client.stop()


# App config
app = FastAPI(
    title="Ferdy’s Twitchiverse",
    summary="Get data from Twitch and send it to the local network.",
    description="An API to manage Twitch-related events, overlay updates, and thermal printing.",
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai"
    }
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get(
    "/overlay",
    response_class=HTMLResponse,
    summary="Display the overlay",
    description="Serves the HTML page that acts as an overlay for OBS."
)
def overlay(request: Request):
    """
    Endpoint to serve the OBS overlay HTML page.
    """
    return templates.TemplateResponse("overlay.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection to communicate with the frontend overlay in real-time.
    Keeps the connection alive and allows broadcasting data.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Keep the WebSocket connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        connected_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connected_clients.remove(websocket)

async def broadcast_message(message: Any):
    """
    Sends a message to all connected WebSocket clients.
    """
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

@app.post(
    "/send-to-overlay",
    summary="Send data to the overlay",
    description="Accepts data and broadcasts it to all connected WebSocket clients for overlay updates.",
    response_description="Acknowledges the broadcast status."
)
async def send_to_overlay(payload: OverlayMessage = Body(...)):
    """
    Endpoint to send data to the overlay via WebSocket.
    Ensures errors in event processing do not trigger a broadcast.
    """
    all_success = True  # ✅ Track success

    try:
        for event_type, event_data in payload.model_dump().items():
            if event_data:  # Only process non-empty events
                success = await event_handlers.handle_event(event_type, event_data, add_clickable_object, remove_clickable_object)
                logger.info(f"🔍 handle_event() returned: {success}")
                if not success:
                    logger.error(f"❌ Event failed: {event_type}")
                    all_success = False  # ✅ Mark failure

        # ✅ Only broadcast if all events succeeded
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

@app.get(
    "/overlay-data",
    summary="Fetch overlay data",
    description="Retrieves the last follower and subscriber from the database.",
    response_description="Returns the last follower and subscriber."
)
async def get_overlay_data():
    """
    Endpoint to fetch the most recent follower and subscriber from the database.
    """
    return {
        "last_follower": get_data("last_follower") or "None",
        "last_subscriber": get_data("last_subscriber") or "None",
        "goal_text": get_data("goal_text") or "None",
        "goal_current": get_data("goal_current") or "None",
        "goal_target": get_data("goal_target") or "None"
    }

# ✅ Background task to process queue events
async def process_queue():
    """ Continuously processes events from the queue """
    while True:
        data = await event_queue.get()

        logger.info(f"📥 Processing event from queue: {data}")

        # ✅ Ensure data is correctly accessed as a dictionary
        if "heat_click" in data:
            click_event = data["heat_click"]  # Extract nested dictionary

            user = click_event.get("user_id")
            x = click_event.get("x")
            y = click_event.get("y")
            clicked_object = click_event.get("object_id")  # ✅ Corrected access

            if user.startswith("A") or user.startswith("U"):
                real_user = "Anonymous" if user.startswith("A") else "Unverified"
            else:
                real_user = firebot.get_username(user)

            logger.info(f"🖱️ Click detected! User: {real_user}, X: {x}, Y: {y}, Object: {clicked_object}")

            if clicked_object == "hidden_star":
                logger.debug("Broadcast star found")
                await broadcast_message({ "hidden": { "action": "found", "user": real_user, "x": x, "y": y } })
                # Reset hidden object
                await firebot.run_effect_list("0977a5a0-e189-11ef-b16a-cbaddbeeb72a")
                # Message to chat
                args = {"args": { "star_user": real_user } }
                await firebot.run_effect_list("3dc732a0-e19b-11ef-b16a-cbaddbeeb72a", args)

        event_queue.task_done()  # Mark task as complete

@app.post(
    "/print",
    summary="Print data to thermal printer",
    description="Send structured data to the thermal printer for printing.",
    response_description="Returns a success message when printing is completed."
)
async def print_data(request: PrintRequest):
    """
    Endpoint to send data to the thermal printer for printing.
    Validates the printer state and sends the print elements.
    """
    if not printer_manager.is_online():
        printer_manager.reconnect()
        if not printer_manager.is_online():
            raise HTTPException(status_code=500, detail="Printer not available")

    try:
        for element in request.print_elements:
            if await printer_manager.print_element(element):
                printer_manager.newline(1)
        printer_manager.cut_paper(partial=True)
        return {"status": "success", "message": "Print done!"}
    except Exception as e:
        logger.error(f"Error during printing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/state",
    summary="Get API state",
    description="Checks the current status of the API and the printer.",
    response_description="Returns the API and printer status."
)
async def status():
    """
    Endpoint to check the current status of the API and printer.
    Provides details about printer availability and operational status.
    """
    is_online = printer_manager.is_online()
    return {
        "status": "online",
        "printer": {
            "is_online": is_online,
            "message": "Printer is operational" if is_online else "Printer is offline",
        },
    }

@app.get(
    "/solar",
    response_class=HTMLResponse,
    summary="Display the Solar-System overlay",
    description="Serves the HTML page that acts as an overlay for OBS."
)
def solarsystem(request: Request):
    """
    Endpoint to serve the OBS overlay HTML page.
    """
    return templates.TemplateResponse("solar-system.html", {"request": request})

@app.get(
    "/raid",
    response_class=HTMLResponse,
    summary="Display the Raid overlay",
    description="Serves the HTML page that acts as an overlay for OBS."
)
def raiders(request: Request):
    """
    Endpoint to serve the OBS overlay HTML page.
    """
    return templates.TemplateResponse("raid.html", {"request": request})

@app.get(
    "/planets",
    summary="Get all planets (raiders)",
    description="Retrieve all planets in the solar system (saved raids).",
    response_description="Returns a list of planets."
)
async def get_all_planets():
    """
    Fetch all saved planets (raiders) from the database.
    """
    planets = get_planets()  # Replace with your database query to fetch raiders
    return [
        {
            "raider_name": raider_name,
            "raid_size": raid_size,
            "angle": angle,
            "distance": distance
        }
        for raider_name, raid_size, angle, distance in planets
    ]

async def add_clickable_object(obj: ClickableObject):
    object_id = obj.object_id

    if object_id in CLICKABLE_OBJECTS:
        return {"status": "error", "message": f"Clickable object {object_id} already exists"}

    # ✅ Ensure we store a dictionary, not a Pydantic model
    CLICKABLE_OBJECTS[object_id] = obj.model_dump()
    update_clickable_objects(CLICKABLE_OBJECTS)

    return {"status": "success", "message": f"Clickable object '{object_id}' added"}

async def remove_clickable_object(object_id: str):
    if object_id not in CLICKABLE_OBJECTS:
        return {"status": "error", "message": f"Clickable object '{object_id}' not found"}

    # ✅ Remove from CLICKABLE_OBJECTS dictionary
    removed_obj = CLICKABLE_OBJECTS.pop(object_id)
    update_clickable_objects(CLICKABLE_OBJECTS)

    logger.info(f"🗑️ Clickable object '{object_id}' removed: {removed_obj}")

    return {"status": "success", "message": f"Clickable object '{object_id}' removed"}

@app.get("/get-clickable-objects")
async def get_clickable_objects():
    """
    Retrieve all currently defined `.clickable` elements.
    """
    return CLICKABLE_OBJECTS

@app.post("/debug")
async def test_debug(payload: Any = Body(...)):
    try:
        # Ensure it's a dictionary before calling .model_dump()
        payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload
        logger.info(f"📡 Debug Payload: {payload_data}")

        # Broadcast to WebSocket clients
        await broadcast_message(payload_data)

        return {"status": "success", "message": "Debug message sent"}

    except Exception as e:
        logger.error(f"❌ Error in /debug: {e}")
        raise HTTPException(status_code=500, detail="Failed to send debug data")


@app.get(
    "/",
    summary="API home",
    description="Provides links to the API documentation, overlay, and status endpoints.",
    response_description="Links to API resources."
)
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Serve the API Overview Homepage."""
    return templates.TemplateResponse("homepage.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
