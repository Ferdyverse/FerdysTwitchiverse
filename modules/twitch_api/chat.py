import logging

logger = logging.getLogger("uvicorn.error.twitch_api_chat")


class TwitchChat:
    async def send_message_as_streamer(self, twitch, channel_id, message):
        try:
            await twitch.send_chat_message(channel_id, channel_id, message)
            logger.info(f"✅ Streamer sent message: {message}")
        except Exception as e:
            logger.error(f"❌ Error sending message as Streamer: {e}")

    async def delete_message(self, twitch, channel_id, message_id):
        return await twitch.delete_chat_message(channel_id, channel_id, message_id)
