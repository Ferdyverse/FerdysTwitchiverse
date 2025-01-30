import asyncio
import json
import logging
import websockets

logger = logging.getLogger("uvicorn.error.heat")

# ✅ Dynamic dictionary for clickable objects (Updated via API)
CLICKABLE_OBJECTS = {}

class HeatAPIClient:
    """
    Connects to Twitch Heat API WebSocket and processes user clicks.
    """

    def __init__(self, channel_id: int, event_queue: asyncio.Queue, websocket_clients: list):
        """
        Initialize the Heat API client.

        :param channel_id: Twitch Channel ID for Heat API.
        :param event_queue: asyncio.Queue to store events.
        :param websocket_clients: List of connected WebSocket clients.
        """
        self.channel_id = channel_id
        self.event_queue = event_queue
        self.websocket_clients = websocket_clients
        self.websocket_task = None
        self.heat_api_url = f"wss://heat-api.j38.net/channel/{self.channel_id}"

    async def connect(self):
        """Connects to the Twitch Heat API WebSocket and sends data to connected clients."""
        try:
            async with websockets.connect(self.heat_api_url) as ws:
                logger.info(f"✅ Connected to Heat API for channel {self.channel_id}")

                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    # Log received data
                    logger.info(f"🔥 Heat API Data: {data}")

                    # Ignore anonymous or unverified users
                    user_id = data.get("user")
                    if user_id.startswith("A") or user_id.startswith("U"):
                        logger.info(f"⚠️ Ignoring click from {user_id} (Anonymous/Unverified)")
                        continue  # Skip processing

                    # Detect what object was clicked
                    processed_click = process_click(data)

                    # Send verified user clicks to the FastAPI queue
                    await self.event_queue.put(processed_click)

                    # Broadcast click to all connected WebSocket clients (Overlay)
                    await self.broadcast_to_clients(processed_click)

        except Exception as e:
            logger.error(f"❌ Error in WebSocket connection: {e}")

    async def broadcast_to_clients(self, data):
        """Sends Heat API events to all connected WebSocket clients (Overlay)."""
        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                await client.send_json(data)  # Send data to WebSocket client
            except Exception as e:
                logger.error(f"WebSocket client error: {e}")
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.websocket_clients.remove(client)

    def start(self):
        """Starts the WebSocket listener asynchronously."""
        if not self.websocket_task:
            self.websocket_task = asyncio.create_task(self.connect())
            logger.info(f"🚀 Heat API listener started for channel {self.channel_id}.")

    def stop(self):
        """Stops the WebSocket listener."""
        if self.websocket_task:
            self.websocket_task.cancel()
            self.websocket_task = None
            logger.info(f"🛑 Heat API listener stopped for channel {self.channel_id}.")

def process_click(data):
    """Detect if a user clicked on a dynamically registered object."""
    user_id = data.get("user")
    x = data.get("x")
    y = data.get("y")

    clicked_object = None
    for obj_name, obj_data in CLICKABLE_OBJECTS.items():
        if (
            obj_data["x"] <= x <= obj_data["x"] + obj_data["width"]
            and obj_data["y"] <= y <= obj_data["y"] + obj_data["height"]
        ):
            clicked_object = obj_name
            break

    return {
        "user_id": user_id,
        "x": x,
        "y": y,
        "object_id": clicked_object,
    }

def update_clickable_objects(new_objects):
    """Update the dictionary of clickable objects dynamically."""
    global CLICKABLE_OBJECTS
    CLICKABLE_OBJECTS = new_objects
    logger.info(f"✅ Updated clickable objects: {CLICKABLE_OBJECTS}")
