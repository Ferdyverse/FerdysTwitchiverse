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

# Own modules
from modules.printer_manager import PrinterManager
from modules.schemas import PrintRequest, OverlayMessage, ClickData, ClickableObject
from modules.db_manager import init_db, get_data, get_planets
from modules.heat_api import HeatAPIClient, update_clickable_objects, CLICKABLE_OBJECTS
from modules.firebot_api import FirebotAPI
from modules import event_handlers
import config

# Configure logger
logger = logging.getLogger("uvicorn.error")

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(module)s - %(message)s"
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
        printer_manager.initialize()

        logger.info("🚀 Starting queue processor")
        asyncio.create_task(process_queue())  # Run in background

        # Load Heat  API
        global heat_api_client
        heat_api_client = HeatAPIClient(config.TWITCH_CHANNEL_ID, event_queue)
        try:
            heat_api_client.start()  # ✅ Start Heat API with error handling
            logger.info("🔥 Heat API started successfully")
        except Exception as e:
            logger.error(f"❌ Heat API startup failed: {e}")

        yield  # The app is running
    except Exception as e:
        logger.error(f"Error during lifespan: {e}")
        yield
    finally:
        logger.info("Shutting down modules")
        printer_manager.shutdown()
        if heat_api_client:
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
    Dynamically calls the appropriate event handler.
    """
    try:
        for event_type, event_data in payload.model_dump().items():
            if event_data:  # Only process non-empty events
                await event_handlers.handle_event(event_type, event_data, add_clickable_object, remove_clickable_object)

        # Broadcast to WebSocket clients
        await broadcast_message(payload.model_dump())
        logger.info(f"📡 Data broadcasted to overlay: {payload.model_dump()}")

        return {"status": "success", "message": "Data sent to overlay"}

    except Exception as e:
        logger.error(f"❌ Error in send_to_overlay: {e}")
        raise HTTPException(status_code=500, detail="Failed to send data")

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
        event = await event_queue.get()  # Wait for an event
        logger.info(f"📥 Processing event from queue: {event}")

        if event.heat_click:
            data = event.heat_click
            clicked_object = data.object_id
            user = data.user_id
            x = data.x
            y = data.y
            real_user = firebot.get_username(user)

            logger.info(f"{real_user} ({user}) clicked on {clicked_object}")

            if clicked_object == "hidden_star":
                await remove_clickable_object(clicked_object)
                await broadcast_message({ "hidden": { "action": "found", "user": real_user, "x": x, "y": y } })

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
        raise HTTPException(status_code=400, detail=f"Object {object_id} already exists")

    # ✅ Ensure we store a dictionary, not a Pydantic model
    CLICKABLE_OBJECTS[object_id] = obj.model_dump()
    update_clickable_objects(CLICKABLE_OBJECTS)

    return {"status": "success", "message": f"Clickable object '{object_id}' added"}

async def remove_clickable_object(object_id: str):
    if object_id not in CLICKABLE_OBJECTS:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found")

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
async def home():
    """
    Default home endpoint with links to API resources.
    """
    return { "docs": "/docs", "overlay": "/overlay", "state": "/state"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
