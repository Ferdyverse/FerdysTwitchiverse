#!/usr/bin/env python3

# FastAPI imports
from fastapi import FastAPI, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import Response
from fastapi import Body
from fastapi import Depends
from sqlalchemy.orm import Session

# Other required imports
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Any, List
import asyncio
import os
import pytz
import random
import inspect
from twitchAPI.type import CustomRewardRedemptionStatus

# Own modules
from modules.printer_manager import PrinterManager
from modules.websocket_handler import websocket_endpoint, broadcast_message
from modules.schemas import PrintRequest, PrintElement, OverlayMessage, ClickData, ClickableObject
from modules.db_manager import init_db, get_data, get_planets, get_db, get_recent_events, get_viewer_stats, save_event
from modules.db_manager import ChatMessage, Viewer
from modules.heat_api import HeatAPIClient, update_clickable_objects, CLICKABLE_OBJECTS
from modules.firebot_api import FirebotAPI
from modules import event_handlers
from modules.twitch_api import TwitchAPI
from modules.twitch_chat import TwitchChatBot
from modules.admin import router as admin_router
from modules.misc import load_sequences
from modules.sequence_runner import get_sequence_names, execute_sequence, reload_sequences, ACTION_SEQUENCES
import config

# ✅ ANSI escape codes for module-based colors
MODULE_COLORS = {
    "twitch_api": "\033[95m",  # Purple
    "twitch_chat": "\033[94m",  # Blue
    "heat_api": "\033[93m",  # Yellow
    "firebot_api": "\033[92m",  # Green
    "printer_manager": "\033[96m",  # Cyan
    "uvicorn.error": "\033[91m",  # Red (Uvicorn errors)
}

# ✅ Reset color
RESET_COLOR = "\033[0m"

# Define the desired local timezone (Change if needed)
LOCAL_TIMEZONE = pytz.timezone("Europe/Berlin")
FALLBACK_COLORS = [
    "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#FF69B4", "#8A2BE2", "#00CED1"
]

class ColorFormatter(logging.Formatter):
    """Custom formatter to apply colors based on module names only."""

    def format(self, record):
        # ✅ Get color based on module (default to white)
        module_color = MODULE_COLORS.get(record.module, "\033[97m")

        log_message = super().format(record)

        return f"{module_color}{log_message}{RESET_COLOR}"

# ✅ Apply to all Uvicorn and custom loggers
formatter = ColorFormatter(
    "%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    datefmt=config.APP_LOG_TIME_FORMAT)

for handler in logging.getLogger("uvicorn").handlers:
    handler.setFormatter(formatter)

DISABLE_HEAT_API = os.getenv("DISABLE_HEAT_API", "false").lower() == "true"
DISABLE_FIREBOT = os.getenv("DISABLE_FIREBOT", "false").lower() == "true"
DISABLE_PRINTER = os.getenv("DISABLE_PRINTER", "false").lower() == "true"
DISABLE_TWITCH = os.getenv("DISABLE_TWITCH", "false").lower() == "true"

ACTION_SEQUENCES = load_sequences()

# Configure the logger
logger = logging.getLogger("uvicorn.error")

# Apply format to all Uvicorn handlers
for handler in logging.getLogger("uvicorn").handlers:
    handler.setFormatter(formatter)

# Instantiate the PrinterManager
printer_manager = PrinterManager()

# Heat API
heat_api_client: HeatAPIClient = None

# Initialize Firebot API Client
firebot = FirebotAPI(config.FIREBOT_API_URL)

# Create an async queue for event sharing
event_queue = asyncio.Queue()

# Global variable for the Twitch module
twitch_api = TwitchAPI(config.TWITCH_CLIENT_ID, config.TWITCH_CLIENT_SECRET, event_queue=event_queue)
twitch_chat = TwitchChatBot(client_id=config.TWITCH_CLIENT_ID, client_secret=config.TWITCH_CLIENT_SECRET, twitch_channel=config.TWITCH_CHANNEL, event_queue=event_queue, twitch_api=twitch_api)

templates = Jinja2Templates(directory="templates")

# Keep track of connected clients
connected_clients = []
clicks: List[ClickData] = []

# Required for Startup and Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event manager for the FastAPI application.
    Initializes modules and ensures Twitch authentication does not block startup.
    """
    logger.info("Initializing modules")
    try:
        init_db()
        asyncio.create_task(process_queue())  # Run queue processor in background

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

        if (not DISABLE_TWITCH) and (config.TWITCH_CLIENT_ID is not None):
            global twitch_api
            global twitch_chat
            asyncio.create_task(twitch_api.initialize())
            asyncio.create_task(twitch_chat.start_chat())
        else:
            if config.TWITCH_CLIENT_ID is None:
                logger.warning("No Twitch login found!")
            logger.info("🚫 Twitch API is disabled.")

        yield

    except Exception as e:
        logger.error(f"Error during lifespan: {e}")
        yield
    finally:
        logger.info("Shutting down modules")

        if not DISABLE_PRINTER:
            printer_manager.shutdown()

        if not DISABLE_HEAT_API and heat_api_client:
            heat_api_client.stop()

        if not DISABLE_TWITCH and twitch_chat.is_running:
            logger.info("🛑 Stopping Twitch ChatBot...")
            await twitch_chat.stop()

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

app.state.twitch_api = twitch_api

# Add the WebSocket route
app.add_api_websocket_route("/ws", websocket_endpoint)
app.include_router(admin_router)

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

# Background task to process queue events
async def process_queue():
    """ Continuously processes events from the queue """
    while True:
        task = await event_queue.get()

        logger.info(f"📥 Processing event from queue: {task}")

        if "function" in task:
            function_name = task["function"]
            parameters = task.get("data", {})

            if parameters == "None":
                parameters = {}

            if function_name in globals():
                func = globals()[function_name]

                if callable(func):
                    try:
                        # ✅ Detect function parameters dynamically
                        sig = inspect.signature(func)
                        param_types = [param.annotation for param in sig.parameters.values()]

                        if param_types and param_types[0] not in [inspect.Parameter.empty, dict]:
                            expected_type = param_types[0]  # Get expected type
                            if isinstance(parameters, dict):
                                parameters = expected_type(**parameters)  # Convert dict to Pydantic Model

                        # ✅ Handle async & sync functions dynamically
                        if inspect.iscoroutinefunction(func):  # Async function
                            await func(parameters) if len(param_types) == 1 else await func(**parameters)
                        else:  # Sync function
                            func(parameters) if len(param_types) == 1 else func(**parameters)

                        logger.info(f"✅ Executed function: {function_name} with parameters: {parameters}")
                        save_event("function_call", None, f"Executed: {function_name} with params: {parameters}")

                    except TypeError as e:
                        logger.error(f"❌ Function execution failed: {e}")
                        save_event("error", None, f"Failed function: {function_name}, Error: {e}")
                else:
                    logger.warning(f"⚠️ '{function_name}' is not callable!")
                    save_event("error", None, f"Attempted call on non-callable: {function_name}")
            else:
                logger.warning(f"⚠️ Function '{function_name}' not found!")
                save_event("error", None, f"Function not found: {function_name}")

        if "command" in task:
            command = task["command"]
            user = task["user"]
            user_id = task["user_id"]

            user_data = await twitch_api.get_user_info(user_id=user_id)

            logger.error(user_data)

            if command == "print":
                message = task.get("message", "")
                logger.info(f"🖨️ Printing requested by {user}: {message}")

                print_request = PrintRequest(
                    print_elements=[
                        PrintElement(type="headline_1", text="Chatogram"),
                        PrintElement(type="image", url=user_data["profile_image_url"]),
                        PrintElement(type="headline_2", text=user),
                        PrintElement(type="message", text=message)
                    ],
                    print_as_image=True
                )

                try:
                    response = await print_data(print_request)  # Call print_data with our constructed request
                    logger.info(f"🖨️ Print status: {response}")
                    await twitch_api.twitch.update_redemption_status(config.TWITCH_CHANNEL_ID, task["reward_id"], task["redeem_id"], CustomRewardRedemptionStatus.FULFILLED)
                except Exception as e:
                    logger.error(f"❌ Error in printing from Twitch command: {e}")
                    await twitch_api.twitch.update_redemption_status(config.TWITCH_CHANNEL_ID, task["reward_id"], task["redeem_id"], CustomRewardRedemptionStatus.CANCELED)
                # await broadcast_message({"message": f"Printing triggered by {user}"})

        # Ensure data is correctly accessed as a dictionary
        if "heat_click" in task:
            click_event = task["heat_click"]  # Extract nested dictionary

            user = click_event.get("user_id")
            x = click_event.get("x")
            y = click_event.get("y")
            clicked_object = click_event.get("object_id")  # Corrected access

            if user.startswith("A") or user.startswith("U"):
                real_user = "Anonymous" if user.startswith("A") else "Unverified"
            else:
                # real_user = firebot.get_username(user)
                real_user = await twitch_api.get_user_info(user_id=user)
                real_user = real_user["display_name"]

            logger.info(f"🖱️ Click detected! User: {real_user}, X: {x}, Y: {y}, Object: {clicked_object}")

            if clicked_object == "hidden_star":
                logger.debug("Broadcast star found")
                await broadcast_message({ "hidden": { "action": "found", "user": real_user, "x": x, "y": y } })
                # Reset hidden object
                await remove_clickable_object(clicked_object)
                # Message to chat
                await twitch_chat.send_message(f"{real_user} hat sich erbarmt und sauber gemacht!")

        if "create_redemtion" in task:
            redemtion = task["create_redemtion"]

            twitch_api.twitch.create_custom_reward(config.TWITCH_CHANNEL_ID, redemtion.get("title"), redemtion.get("cost"))

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
        if request.print_as_image:
            # Print a image
            pimage = await printer_manager.create_image(elements=request.print_elements)
            printer_manager.printer.image(pimage,
                        high_density_horizontal=True,
                        high_density_vertical=True,
                        impl="bitImageColumn",
                        fragment_height=960,
                        center=True)
        else:
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
    description="Checks the current status of all modules (Printer, Twitch, Heat API, Firebot, etc.).",
    response_description="Returns the API and module statuses."
)
async def status():
    """
    Dynamically fetches the status of all active modules.
    """

    # Check printer status
    printer_status = {
        "is_online": printer_manager.is_online(),
        "message": "Printer is operational" if printer_manager.is_online() else "Printer is offline",
    }

    # Check Firebot status
    firebot_status = {
        "is_connected": firebot is not None,
        "message": "Firebot API connected" if firebot else "Firebot API offline",
    }

    # Check heat api status
    heat_api_status = {
        "is_connected": heat_api_client.is_connected,
        "message": "Heat API is connected" if heat_api_client.is_connected else "Heat API is offline"
    }

    # Check Twitch API & Chat Bot
    twitch_api_status = {
        "is_authenticated": twitch_api is not None,
        "message": "Twitch API authenticated" if twitch_api else "Twitch API not authenticated",
    }

    twitch_chat_status = {
        "is_running": twitch_chat is not None and twitch_chat.is_running,
        "message": "Twitch Chat Bot running" if twitch_chat and twitch_chat.is_running else "Twitch Chat Bot offline",
    }

    return {
        "status": "online",
        "printer": printer_status,
        "heat_api": heat_api_status,
        "firebot": firebot_status,
        "twitch_api": twitch_api_status,
        "twitch_chat": twitch_chat_status,
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
        logger.error(f"Clickable object {object_id} already exists")
        return {"status": "error", "message": f"Clickable object {object_id} already exists"}

    # Ensure we store a dictionary, not a Pydantic model
    CLICKABLE_OBJECTS[object_id] = obj.model_dump()
    update_clickable_objects(CLICKABLE_OBJECTS)

    return {"status": "success", "message": f"Clickable object '{object_id}' added"}

async def remove_clickable_object(object_id):
    # Remove from CLICKABLE_OBJECTS dictionary
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

@app.post("/trigger-overlay/")
async def trigger_overlay(request: Request):
    body = await request.json()
    action = body.get("action")
    data = body.get("data", {})

    if not action:
        raise HTTPException(status_code=400, detail="Missing action type")

    if action in ACTION_SEQUENCES:
        await execute_sequence(action, event_queue)  # Pass event_queue
    else:
        save_event("overlay_action", None, f"Direct overlay action: {action} with data: {data}")
        await broadcast_message({"overlay_event": {"action": action, "data": data}})

    return {"status": "success", "message": f"Overlay triggered: {action}"}

@app.post("/reload-sequences")
async def reload_sequences_endpoint():
    """Manually reload sequences from YAML file."""
    await reload_sequences()
    return {"status": "success", "message": "Sequences reloaded!"}

@app.get("/chat", response_class=HTMLResponse)
async def get_chat_messages(db: Session = Depends(get_db)):
    """
    Retrieve the last 50 chat messages from the database, formatted identically to WebSocket messages.
    """
    messages = db.query(
        ChatMessage.id,
        ChatMessage.message,
        ChatMessage.timestamp,
        Viewer.display_name.label("username"),
        Viewer.profile_image_url.label("avatar"),
        Viewer.color.label("user_color"),
        Viewer.badges.label("badges"),
        ChatMessage.viewer_id.label("twitch_id")
    ).join(Viewer, ChatMessage.viewer_id == Viewer.twitch_id, isouter=True) \
    .order_by(ChatMessage.timestamp.desc()) \
    .limit(50).all()

    if not messages:
        return "<p class='chat-placeholder text-gray-500 text-center'>No messages yet...</p>"

    chat_html = ""

    for msg in reversed(messages):  # Reverse to show oldest messages first
        username = msg.username or "Unknown"
        avatar_url = msg.avatar or "/static/images/default_avatar.png"
        user_color = msg.user_color or random.choice(FALLBACK_COLORS)

        # Convert timestamp to local timezone
        utc_time = msg.timestamp.replace(tzinfo=pytz.utc)  # Ensure UTC
        local_time = utc_time.astimezone(LOCAL_TIMEZONE).strftime("%H:%M")  # Convert to HH:MM

        # Handle badges (If available)
        badge_html = ""
        if msg.badges:
            badge_list = msg.badges.split(",")  # Convert stored CSV to list
            badge_html = "".join([f'<img src="{badge}" class="chat-badge" alt="badge">' for badge in badge_list])

        # HTML structure (Matches WebSocket messages)
        chat_html += f"""
            <div class="chat-message flex items-start space-x-3 p-3 rounded-md bg-gray-800 border border-gray-700 mb-2 shadow-sm"
                data-message-id="{msg.id}" data-user-id="{msg.twitch_id}">
                <img src="{avatar_url}" alt="{username}" class="chat-avatar w-10 h-10 rounded-full border border-gray-600">
                <div class="chat-content flex flex-col w-full">
                    <div class="chat-header flex justify-between items-center text-gray-400 text-sm mb-1">
                        <div class="chat-username font-bold" style="color: {user_color};">{badge_html}{username}</div>
                        <div class="chat-timestamp text-xs">{local_time}</div>
                    </div>
                    <div class="chat-text text-gray-300 break-words bg-gray-900 p-2 rounded-lg w-fit max-w-3xl">
                        {msg.message}
                    </div>
                </div>
            </div>
        """

    return Response(chat_html, media_type="text/html")

@app.get("/events/", response_class=HTMLResponse)
def get_events():
    """
    Retrieve the last 50 stored events and return them as an HTML snippet.
    """
    events = get_recent_events()

    if not events:
        return "<p class='text-center text-gray-400'>No events yet...</p>"

    event_html = ""

    for event in reversed(events):
        event_type = event.event_type.replace("_", " ").capitalize()
        username = event.username if event.username else "Unknown"
        timestamp = event.timestamp.strftime('%Y-%m-%d %H:%M:%S')

        # Apply color-coded styles for different event types
        if "admin_action" in event.event_type:
            color_class = "border-blue-500 bg-blue-900/20"
        elif "button_click" in event.event_type:
            color_class = "border-yellow-500 bg-yellow-900/20"
        elif "function_call" in event.event_type:
            color_class = "border-green-500 bg-green-900/20"
        elif "error" in event.event_type:
            color_class = "border-red-500 bg-red-900/20"
        else:
            color_class = "border-gray-500 bg-gray-800"

        # ✅ **EXACT format as you requested**
        event_html += f"""
            <div class="p-3 mb-2 rounded-md shadow-md border-l-4 {color_class}">
                <!-- First Line: Action (Bold) -->
                <div class="font-semibold text-white">{event_type}</div>

                <!-- Second Line: Date (Small) -->
                <div class="text-xs text-gray-400">{timestamp}</div>

                <!-- Third Line: Details -->
                <div class="mt-2 text-gray-300 text-sm">{event.message}</div>

                <!-- Fourth Line: Username (Yellow, Small) -->
                <div class="mt-1 text-xs text-yellow-400 font-semibold">{username}</div>
            </div>
        """

    return HTMLResponse(content=event_html)

@app.get("/viewers/{twitch_id}")
async def get_viewer(twitch_id: int):
    """Fetch viewer data along with stats."""
    viewer_data = get_viewer_stats(twitch_id)

    if not viewer_data:
        try:
            await twitch_api.get_user_info(user_id=twitch_id)
        except:
            raise HTTPException(status_code=404, detail="Viewer not found")

    return viewer_data

@app.post("/send-chat/")
async def send_chat_message(
    message: str = Form(...),
    sender: str = Form("streamer")  # Default to Bot
):
    """
    Send a chat message from the admin panel as either the Bot or the Streamer.
    """
    if not message.strip():
        return Response("", media_type="text/html")  # Don't send empty messages

    if sender == "bot":
        await twitch_chat.send_message(message)
    elif sender == "streamer":
        await twitch_api.send_message_as_streamer(message)

    # Return an empty response (WebSocket will update the chat)
    return Response("", media_type="text/html")

@app.get(
    "/",
    summary="API home",
    description="Provides links to the API documentation, overlay, and status endpoints.",
    response_description="Links to API resources.",
    response_class=HTMLResponse)
async def homepage(request: Request):
    """Serve the API Overview Homepage."""
    sequence_names = get_sequence_names()
    return templates.TemplateResponse("homepage.html", {"request": request, "sequence_names": sequence_names})

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
