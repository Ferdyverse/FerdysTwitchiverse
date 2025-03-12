import logging
from modules.websocket_handler import broadcast_message

logger = logging.getLogger("uvicorn.error.twitch_api")

class TwitchRewards:
    async def handle_channel_point_redeem(self, data):
        logger.info(f"🎟️ Channel Point Redemption Event: {data}")
        await broadcast_message({
            "alert": {
                "type": "redemption",
                "user": data.event.user_name,
                "message": f"{data.event.reward.title}: {data.event.user_input}"
            }
        })
