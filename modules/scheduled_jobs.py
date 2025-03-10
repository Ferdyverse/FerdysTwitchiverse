import logging
import random
import asyncio
from database.crud.scheduled_jobs import get_scheduled_job_by_id
from database.crud.scheduled_messages import get_random_message_from_category
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence

logger = logging.getLogger("uvicorn.error.scheduled_jobs")


def process_scheduled_job_sync(job_id: int, app):
    """Runs the async function process_scheduled_job() inside an event loop."""
    asyncio.run(process_scheduled_job(job_id, app))


async def process_scheduled_job(job_id: int, app):
    """Processes a single scheduled job using async database functions."""

    try:
        job = get_scheduled_job_by_id(job_id)
        twitch_chat = app.state.twitch_chat

        if not job:
            logger.warning(f"⚠️ Job {job_id} not found, skipping.")
            return

        logger.info(f"🚀 Starting job {job['job_type']} (ID: {job_id})")

        # ─── Handle Twitch Chat Message ───────────────────────────
        if job["job_type"] == "twitch_message":
            message_text = job["payload"].get("text")
            message_category = job["payload"].get("category")

            if not message_text and message_category:
                message_text = get_random_message_from_category(message_category)

                if not message_text:
                    logger.warning(f"⚠️ No messages found in pool for category '{message_category}', skipping.")
                    return

            if message_text:
                await twitch_chat.send_message(message_text)
                logger.info(f"✅ Sent scheduled message: {message_text}")

        # ─── Execute Sequence ────────────────────────────────────
        elif job["job_type"] == "sequence":
            sequence = job["payload"].get("sequence")
            if sequence:
                logger.info(f"🎬 Executing sequence: {sequence}")
                await execute_sequence(sequence, app.state.event_queue)

        # ─── Send Overlay Event ──────────────────────────────────
        elif job["job_type"] == "overlay_event":
            event_data = job["payload"]
            await broadcast_message(event_data)
            logger.info(f"📡 Triggered overlay event: {event_data}")

        # ─── Handle One-Time Job ─────────────────────────────────
        elif job["job_type"] == "date":
            logger.info(f"🔔 Running one-time scheduled job {job['event_id']}")
            # TODO: Update job status in DB to mark it as completed

        # ─── Handle Cron Jobs ────────────────────────────────────
        elif job["job_type"] == "cron":
            logger.info(f"⏰ Running cron job {job['event_id']}")

        else:
            logger.warning(f"⚠️ Unknown job type: {job['job_type']}, skipping.")

    except Exception as e:
        logger.error(f"❌ Error processing job {job_id}: {e}")
