import logging
from modules.websocket_handler import broadcast_message

logger = logging.getLogger("uvicorn.error.twitch_api")

class TwitchChat:
    async def send_message_as_streamer(self, twitch, channel_id, message):
        try:
            await twitch.send_chat_message(channel_id, channel_id, message)
            logger.info(f"✅ Streamer sent message: {message}")
        except Exception as e:
            logger.error(f"❌ Error sending message as Streamer: {e}")
