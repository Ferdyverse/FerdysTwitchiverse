import logging
import random
import asyncio
from database.session import get_db
from database.crud.scheduled_jobs import get_scheduled_job_by_id
from database.base import ScheduledMessagePool
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence

logger = logging.getLogger("uvicorn.error.scheduled_jobs")

def process_scheduled_job_sync(job_id: int, app):
    """Runs the async function process_scheduled_job() inside an event loop."""
    asyncio.run(process_scheduled_job(job_id, app))

async def process_scheduled_job(job_id: int, app):
    """Processes a single scheduled job asynchronously."""

    async with get_db() as db:
        job = await get_scheduled_job_by_id(job_id, db)
        twitch_chat = app.state.twitch_chat
        logger.info(f"Starting job {job}")

        # When the job failed
        if not job:
            logger.warning(f"⚠️ Job {job_id} not found, skipping.")
            return  # Job was deleted or invalid

        # Send a chat message
        if job.job_type == "twitch_message":
            message_text = job.payload.get("text")
            message_category = job.payload.get("category")

            logger.info(f"text: {message_text}, category: {message_category}")

            if message_text is None and message_category:
                logger.info(f"Searching for messages in {message_category}")

                # If message is empty, pick one from the pool
                result = await db.execute(
                    select(ScheduledMessagePool.message).filter(
                        ScheduledMessagePool.category == message_category,
                        ScheduledMessagePool.enabled == True
                    )
                )
                pool_messages = result.scalars().all()

                if pool_messages:
                    message_text = random.choice(pool_messages)
                else:
                    logger.warning(f"⚠️ No messages found in pool for category '{message_category}', skipping.")

                logger.info(f"Found Message to send: {message_text}")

            if message_text:
                await twitch_chat.send_message(message_text)
                logger.info(f"✅ Sent scheduled message: {message_text}")

        # Run a sequence
        elif job.job_type == "sequence":
            job_data = job.payload
            sequence = job_data.get("sequence")
            logger.info(f"Execute sequence: {sequence}")
            await execute_sequence(sequence, app.state.event_queue)

        # Send something to the overlay
        elif job.job_type == "overlay_event":
            event_data = job.payload
            await broadcast_message(event_data)
            logger.info(f"✅ Triggered overlay event: {event_data}")

        # Date -> Currently not used
        elif job.job_type == "date":
            logger.info(f"🔔 Running one-time scheduled job {job.event_id}")
            job.active = False  # Mark as completed
            await db.commit()

        # Cron -> Also not used
        elif job.job_type == "cron":
            logger.info(f"🔔 Running cron job {job.event_id}")

        else:
            logger.warning(f"⚠️ Unknown job type: {job.job_type}, skipping.")
