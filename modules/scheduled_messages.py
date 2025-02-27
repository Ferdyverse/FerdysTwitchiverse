import asyncio
import random
import datetime
import logging
from database.session import get_db
from database.base import ScheduledMessage, ScheduledMessagePool
from modules.twitch_chat import TwitchChatBot

logger = logging.getLogger("uvicorn.error.scheduled_messages")

async def process_scheduled_messages(twitch_chat: TwitchChatBot):
    """ Continuously checks and sends scheduled messages. """
    db = next(get_db())

    now = datetime.datetime.now(datetime.timezone.utc)
    messages = db.query(ScheduledMessage).filter(
        ScheduledMessage.enabled == True
    ).all()

    # Prevent all messages from sending immediately on startup
    logger.info("Rescheduling messages!")
    for msg in messages:
        if msg.next_run.tzinfo is None:
            msg.next_run = msg.next_run.replace(tzinfo=datetime.timezone.utc)
        if msg.next_run <= now:
            new_delay = random.randint(0, msg.interval)  # Random delay within the interval
            msg.next_run = now + datetime.timedelta(seconds=new_delay)
            logger.info(f"⏳ Delayed '{msg.message if msg.message is not None else msg.category}' by {new_delay} seconds.")

    db.commit()
    db.close()

    # Start the main loop
    while True:
        db = next(get_db())
        now = datetime.datetime.now(datetime.timezone.utc)

        messages = db.query(ScheduledMessage).filter(
            ScheduledMessage.enabled == True,
            ScheduledMessage.next_run <= now
        ).all()

        for msg in messages:
            message_text = msg.message

            logger.info(f"text: {msg.message}, cat: {msg.category}")

            if message_text is not None and msg.category:
                logger.info(f"Searching for messages in {msg.category}")
                # If message is empty, pick one from the pool
                pool_messages = db.query(ScheduledMessagePool).filter(
                    ScheduledMessagePool.category == msg.category,
                    ScheduledMessagePool.enabled == True
                ).all()

                if pool_messages:
                    message_text = random.choice(pool_messages).message
                else:
                    logger.warning(f"⚠️ No messages found in pool for category '{msg.category}', skipping.")
                    continue

                logger.info(f"Found Message so send: {message_text}")

            if message_text:
                await twitch_chat.send_message(message_text)
                logger.info(f"✅ Sent scheduled message: {message_text}")

            # Update next_run
            msg.next_run = now + datetime.timedelta(seconds=msg.interval)
            db.commit()

        db.close()
        await asyncio.sleep(60)  # Run every minute
