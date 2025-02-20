import logging
import asyncio
from contextlib import asynccontextmanager
import config
import os
from database.session import init_db
from modules.twitch_api import TwitchAPI
from modules.twitch_chat import TwitchChatBot
from modules.obs_api import OBSController
from modules.heat_api import HeatAPIClient
from modules.printer_manager import PrinterManager
from modules.sequence_runner import load_sequences
from modules.event_queue import event_queue
from modules.queue_processor import process_queue

logger = logging.getLogger("uvicorn.error.lifespan")

# Global Modules
event_queue = asyncio.Queue()
printer_manager = PrinterManager()
twitch_api = TwitchAPI(config.TWITCH_CLIENT_ID, config.TWITCH_CLIENT_SECRET, event_queue=event_queue)
twitch_chat = TwitchChatBot(client_id=config.TWITCH_CLIENT_ID, client_secret=config.TWITCH_CLIENT_SECRET, twitch_channel=config.TWITCH_CHANNEL, event_queue=event_queue, twitch_api=twitch_api)
obs = OBSController(config.OBS_WS_HOST, config.OBS_WS_PORT, config.OBS_WS_PASSWORD)
heat_api_client = None

@asynccontextmanager
async def lifespan(app):
    """Lifecycle event manager for the FastAPI application."""
    logger.info("🔧 Initializing Modules...")

    try:

        init_db()

        # Start queue processor
        asyncio.create_task(process_queue(app, event_queue))

        # Initialize Printer
        if not config.DISABLE_PRINTER:
            printer_manager.initialize()
        else:
            logger.info("🚫 Printer is disabled.")

        # Initialize Heat API
        if not config.DISABLE_HEAT_API:
            global heat_api_client
            heat_api_client = HeatAPIClient(config.TWITCH_CHANNEL_ID, event_queue)
            heat_api_client.start()
        else:
            logger.info("🚫 Heat API is disabled.")

        # Initialize Twitch API & Chat
        if not config.DISABLE_TWITCH:
            asyncio.create_task(twitch_api.initialize())
            asyncio.create_task(twitch_chat.start_chat())
            app.state.twitch_api = twitch_api
            app.state.twitch_chat = twitch_chat

        # Initialize OBS
        if not config.DISABLE_OBS:
            await obs.initialize()
            app.state.obs = obs

        # Load Sequences
        load_sequences()

        yield
    finally:
        logger.info("🔻 Shutting Down Modules...")

        if not config.DISABLE_PRINTER:
            printer_manager.shutdown()

        if not config.DISABLE_HEAT_API and heat_api_client:
            heat_api_client.stop()

        if not config.DISABLE_TWITCH and twitch_chat.is_running:
            await twitch_chat.stop()

        if not config.DISABLE_OBS:
            await obs.disconnect()
