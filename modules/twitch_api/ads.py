import config
import datetime
import logging
import pytz
from modules.websocket_handler import broadcast_message
from database.crud.events import save_event

logger = logging.getLogger("uvicorn.error.twitch_api")


class TwitchAds:
    async def get_ad_schedule(self, twitch):
        """Get the current AD schedule and store the event using the CRUD function."""
        try:
            ads = await twitch.get_ad_schedule(config.TWITCH_CHANNEL_ID)

            # Extract relevant ad data
            snooze_count = ads.snooze_count  # Number of available snoozes
            snooze_refresh = ads.snooze_refresh_at  # When snoozes refresh
            next_ad_time = ads.next_ad_at  # When the next ad will play
            duration = ads.duration  # Duration of the next ad (in seconds)
            last_ad = ads.last_ad_at  # Last played ad timestamp (can be None)
            preroll_free_time = (
                ads.preroll_free_time
            )  # Time left without preroll ads (in seconds)

            # Ensure timestamps are in UTC and convert to local timezone
            utc_next_ad_time = next_ad_time.replace(tzinfo=pytz.utc)
            local_next_ad_time = utc_next_ad_time.astimezone(config.LOCAL_TIMEZONE)
            local_next_ad_timestamp = int(local_next_ad_time.timestamp())
            current_timestamp = int(
                datetime.datetime.now(datetime.timezone.utc).timestamp()
            )

            # Format ad time for logs
            formatted_time = local_next_ad_time.strftime("%H:%M:%S")

            # If next ad is already in the past, return "unknown"
            if (local_next_ad_timestamp - current_timestamp) < 1:
                return {"status": "unknown"}

            save_event(
                event_type="ad_break",
                viewer_id=None,
                message=f"Ad break starts at {formatted_time} for {duration} seconds",
            )

            # Send alert to admin panel
            await broadcast_message(
                {
                    "admin_alert": {
                        "type": "ad_break",
                        "duration": duration,
                        "start_time": local_next_ad_timestamp,
                        "snooze_count": snooze_count,
                        "snooze_refresh": snooze_refresh,
                        "last_ad": last_ad,
                        "preroll_free_time": preroll_free_time,
                    }
                }
            )

            logger.info(
                f"📢 Ad break scheduled at {formatted_time} for {duration} seconds"
            )

            return {"duration": duration, "start_time": local_next_ad_time}

        except Exception as e:
            logger.error(f"❌ Error retrieving ad schedule: {e}")
            return {"status": "error", "message": str(e)}
