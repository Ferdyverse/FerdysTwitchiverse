import asyncio
import json
import logging
import websockets

logger = logging.getLogger("uvicorn.error")

class HeatAPIClient:
    """
    Handles Twitch Heat API WebSocket connection.
    Connects to the Twitch Heat API and processes incoming heat events.
    """

    def __init__(self, channel_id: int):
        """
        Initialize the Heat API client.

        :param channel_id: Twitch channel ID for Heat API connection.
        """
        self.channel_id = channel_id
        self.heat_api_url = f"wss://heat-api.j38.net/channel/{channel_id}"
        self.websocket_task = None
        self.is_running = False

    async def connect(self):
        """Connects to the Twitch Heat API WebSocket."""
        try:
            async with websockets.connect(self.heat_api_url) as ws:
                self.is_running = True
                logger.info(f"✅ Connected to Heat API for channel {self.channel_id}")

                while self.is_running:
                    message = await ws.recv()
                    data = json.loads(message)

                    # Log and process received data
                    logger.info(f"🔥 Heat API Data: {data}")
                    await self.process_heat_data(data)

        except Exception as e:
            logger.error(f"❌ Error in WebSocket connection: {e}")
        finally:
            self.is_running = False

    async def process_heat_data(self, data):
        """
        Process incoming Heat API data.

        :param data: Parsed JSON data from the WebSocket.
        """
        event_type = data.get("event", "unknown")

        if event_type == "click":
            logger.info(f"🖱️ Click at X:{data.get('x')}, Y:{data.get('y')} by {data.get('user')}")
            # TODO:
            #       - Trigger overlay effects, save clicks, or broadcast WebSocket updates
            #       - Check if it is possible to match the user to an actual twitch user

        elif event_type == "heatmap":
            logger.info(f"🔥 Heatmap data received: {data}")
            # TODO: Store heatmap data for later use

    def start(self):
        """Starts the WebSocket listener asynchronously."""
        if not self.websocket_task:
            self.websocket_task = asyncio.create_task(self.connect())
            logger.info("🚀 Heat API listener started.")

    def stop(self):
        """Stops the WebSocket listener."""
        if self.websocket_task:
            self.websocket_task.cancel()
            self.websocket_task = None
            self.is_running = False
            logger.info("🛑 Heat API listener stopped.")
