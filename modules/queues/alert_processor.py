import asyncio
import inspect
import logging
from fastapi import Depends
from twitchAPI.type import CustomRewardRedemptionStatus
from sqlalchemy.orm import Session

from database.session import get_db
from database.crud.events import save_event
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence
from modules.queues.function_registry import get_function
import config

logger = logging.getLogger("uvicorn.error.alert_queue_processor")

worker_count = 0  # Track how many times this function is started

async def process_alert_queue(app):
    """ Continuously processes events from the queue """

    global worker_count
    worker_count += 1
    logger.info(f"🚀 Starting Alert Queue Processor #{worker_count}")

    twitch_api = app.state.twitch_api
    twitch_chat = app.state.twitch_chat
    obs = app.state.obs
    alert_queue = app.state.alert_queue

    db = next(get_db())
    try:
        while True:
            task = await alert_queue.get()
            logger.info(f"📥 Processing event from queue: {task}")

            # Handle function execution
            if "follow" in task:
                # New follower event
                logger.info("follow")

            if "subscribe" in task:
                # New Subscriber
                logger.info("subscribe")

            alert_queue.task_done()
    except Exception as e:
        print(f"❌ Error in Event Queue Processor: {e}")

    finally:
        db.close()
