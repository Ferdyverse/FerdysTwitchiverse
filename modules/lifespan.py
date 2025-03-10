import logging
import asyncio
from contextlib import asynccontextmanager
import config
import os
from modules.twitch_api import TwitchAPI
from modules.twitch_chat import TwitchChatBot
from modules.obs_api import OBSController
from modules.heat_api import HeatAPIClient
from modules.printer_manager import PrinterManager
from modules.sequence_runner import load_sequences
from modules.queues.manager import event_queue, alert_queue
from modules.queues.function_registry import register_function
from modules.apscheduler import start_scheduler, shutdown_scheduler
from modules.queues.event_processor import process_event_queue
from modules.queues.alert_processor import process_alert_queue

from routes.overlay import send_to_overlay
from modules.sequence_runner import reload_sequences
from routes.print import print_data

logger = logging.getLogger("uvicorn.error.lifespan")

# Global Modules
printer_manager = PrinterManager()
heat_api_client = None

@asynccontextmanager
async def lifespan(app):
    """Lifecycle event manager for the FastAPI application."""
    logger.info("🔧 Initializing Modules...")

    use_mock_api = config.USE_MOCK_API

    twitch_api = TwitchAPI(client_id=config.TWITCH_CLIENT_ID, client_secret=config.TWITCH_CLIENT_SECRET, test_mode=use_mock_api)

    twitch_chat = None
    if not use_mock_api:
        twitch_chat = TwitchChatBot(client_id=config.TWITCH_CLIENT_ID, client_secret=config.TWITCH_CLIENT_SECRET, twitch_channel=config.TWITCH_CHANNEL, twitch_api=twitch_api)

    try:

        # Init Queues
        app.state.event_queue = event_queue
        app.state.alert_queue = alert_queue

        # Initialize Printer
        if not config.DISABLE_PRINTER:
            printer_manager.initialize()
            app.state.printer = printer_manager
        else:
            logger.info("🚫 Printer is disabled.")
            app.state.printer = None

        # Initialize Heat API
        if not config.DISABLE_HEAT_API and not use_mock_api:
            global heat_api_client
            heat_api_client = HeatAPIClient(app, config.TWITCH_CHANNEL_ID)
            heat_api_client.start()
            app.state.heat_api = heat_api_client
        else:
            logger.info("🚫 Heat API is disabled.")
            app.state.heat_api = None


        # Initialize Twitch API & Chat
        if not config.DISABLE_TWITCH:
            asyncio.create_task(twitch_api.initialize(app))
            if not use_mock_api:
                asyncio.create_task(twitch_chat.start_chat(app))
            app.state.twitch_api = twitch_api
            app.state.twitch_chat = twitch_chat
            if not use_mock_api:
                register_function("twitch_chat.send_message", twitch_chat.send_message)
                start_scheduler(app)
        else:
            logger.info("🚫 Twitch API is disabled.")
            app.state.twitch_api = None
            app.state.twitch_chat = None

        # Initialize OBS
        obs = None
        if not config.DISABLE_OBS:
            obs = OBSController(config.OBS_WS_HOST, config.OBS_WS_PORT, config.OBS_WS_PASSWORD)
            await obs.initialize()
            app.state.obs = obs
            register_function("obs.toggle_source", obs.toggle_source)
            register_function("obs.switch_scene", obs.switch_scene)
        else:
            logger.info("🚫 OBS API is disabled.")
            app.state.obs = None

        # Load Sequences
        load_sequences()

        register_function("send_to_overlay", send_to_overlay)
        register_function("reload_sequences", reload_sequences)
        register_function("print_data", print_data)

        # Start queue processors once
        asyncio.create_task(process_event_queue(app))
        #asyncio.create_task(process_alert_queue(app))

        await asyncio.sleep(1)

        yield
    finally:
        logger.info("🔻 Shutting Down Modules...")

        if not config.DISABLE_PRINTER:
            printer_manager.shutdown()

        if not config.DISABLE_HEAT_API and heat_api_client:
            heat_api_client.stop()

        if not config.DISABLE_TWITCH and twitch_chat:
            await twitch_chat.stop()
            shutdown_scheduler()

        if not config.DISABLE_OBS:
            await obs.disconnect()
