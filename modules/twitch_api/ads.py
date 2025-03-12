import logging
from modules.websocket_handler import broadcast_message
from database.crud.events import save_event

logger = logging.getLogger("uvicorn.error.twitch_api")

class TwitchAds:
    async def handle_ad_break(self, data: dict):
        ad_length = data.event.duration_seconds
        logger.info(f"📢 Upcoming ad break! Duration: {ad_length}s")

        await broadcast_message({
            "admin_alert": {
                "type": "ad_break",
                "duration": ad_length
            }
        })

        save_event("ad_break", None, f"Ad break scheduled for {ad_length} seconds")
