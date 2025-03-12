import logging

logger = logging.getLogger("uvicorn.error.twitch_api")

class TwitchModeration:
    async def handle_ban(self, data: dict):
        moderator = data.event.moderator_user_name
        target = data.event.user_name
        logger.info(f"🚨 {moderator} banned {target}!")
