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

    def __init__(self, channel_id: int, event_queue: asyncio.Queue):
        """
        Initialize the Heat API client.

        :param channel_id: Twitch Channel ID for Heat API.
        :param event_queue: asyncio.Queue to store events.
        """
        self.channel_id = channel_id
        self.event_queue = event_queue
        self.websocket_task = None
        self.heat_api_url = f"wss://heat-api.j38.net/channel/{self.channel_id}"

    async def connect(self):
        """Connects to the Twitch Heat API WebSocket and sends data to connected clients."""
        while True:
            try:
                logger.info(f"🔗 Connecting to Heat API WebSocket: {self.heat_api_url}")

                async with websockets.connect(self.heat_api_url, ping_interval=30) as ws:  # Ping alle 30 Sekunden
                    logger.info(f"✅ Connected to Heat API for channel {self.channel_id}")

                    # Start background ping task
                    asyncio.create_task(self.send_ping(ws))

                    while True:
                        message = await ws.recv()
                        data = json.loads(message)

                        # Log received data
                        logger.info(f"🔥 Heat API Data: {data}")

                        if data.get("type") == "system":
                            continue
                        elif data.get("type") == "click":
                            # Ignore anonymous or unverified users
                            user_id = data.get("id")

                            # We need to multiply with the canvas size
                            coord_x = int(float(data.get("x")) * 1920)
                            coord_y = int(float(data.get("y")) * 1080)

                            logger.info(f"🔥 user: {user_id} | x: {coord_x} | y: {coord_y}")

                            if user_id.startswith("A") or user_id.startswith("U"):
                                username = "Anonymous" if user_id.startswith("A") else "Unverified"
                                logger.info(f"⚠️ Got click from {username}")

                            # Detect what object was clicked
                            processed_click = process_click(data, coord_x, coord_y)
                            logger.info(f"Clicked Object: {processed_click}")

                            # Send verified user clicks to the FastAPI queue
                            await self.event_queue.put(processed_click)

            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError) as e:
                logger.error(f"❌ WebSocket connection error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Retry after delay
            except Exception as e:
                logger.error(f"❌ Unexpected WebSocket error: {e}")
                await asyncio.sleep(5)  # Retry in case of unexpected failure

    async def send_ping(self, ws):
        """Send periodic ping messages to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(120)  # Send ping every 120 seconds
                await ws.ping()
                logger.debug("📡 Sent WebSocket ping to Heat API")
        except Exception as e:
            logger.warning(f"⚠️ Ping failed: {e}")
            await self.connect()

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

def process_click(data, x, y):
    """Detect if a user clicked on a dynamically registered object."""
    user_id = data.get("id")

    logger.info(f"Searching for object at {x} : {y}")

    clicked_object = None
    for obj_name, obj_data in CLICKABLE_OBJECTS.items():
        if (
            obj_data["x"] <= x <= obj_data["x"] + obj_data["width"]
            and obj_data["y"] <= y <= obj_data["y"] + obj_data["height"]
        ):
            clicked_object = obj_name
            break

    return {
        "heat_click": {
            "user_id": user_id,
            "x": x,
            "y": y,
            "object_id": clicked_object,
        }
    }

def update_clickable_objects(new_objects):
    """Update the dictionary of clickable objects dynamically."""
    global CLICKABLE_OBJECTS
    CLICKABLE_OBJECTS = new_objects
    logger.info(f"✅ Updated clickable objects: {CLICKABLE_OBJECTS}")
