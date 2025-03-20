import logging
from twitchAPI.type import AuthScope
import config
from modules.twitch_api import (
    TwitchAuth,
    TwitchEventSub,
    TwitchChat,
    TwitchUsers,
    TwitchAds,
    TwitchRewards,
)

logger = logging.getLogger("uvicorn.error.twitch_api_client")

REAL_SCOPES = [
    AuthScope.ANALYTICS_READ_EXTENSION,
    AuthScope.ANALYTICS_READ_GAMES,
    AuthScope.BITS_READ,
    AuthScope.CHANNEL_MANAGE_BROADCAST,
    AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
    AuthScope.CHANNEL_MODERATE,
    AuthScope.CHANNEL_READ_ADS,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.CHAT_EDIT,
    AuthScope.CHAT_READ,
    AuthScope.CLIPS_EDIT,
    AuthScope.MODERATION_READ,
    AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
    AuthScope.MODERATOR_MANAGE_AUTOMOD,
    AuthScope.MODERATOR_MANAGE_BANNED_USERS,
    AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS,
    AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
    AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS,
    AuthScope.MODERATOR_MANAGE_SHOUTOUTS,
    AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS,
    AuthScope.MODERATOR_MANAGE_WARNINGS,
    AuthScope.MODERATOR_READ_CHATTERS,
    AuthScope.MODERATOR_READ_FOLLOWERS,
    AuthScope.MODERATOR_READ_MODERATORS,
    AuthScope.MODERATOR_READ_VIPS,
    AuthScope.USER_EDIT_BROADCAST,
    AuthScope.USER_MANAGE_BLOCKED_USERS,
    AuthScope.USER_READ_BLOCKED_USERS,
    AuthScope.USER_READ_CHAT,
    AuthScope.USER_READ_EMAIL,
    AuthScope.USER_READ_FOLLOWS,
    AuthScope.USER_WRITE_CHAT,
    AuthScope.WHISPERS_EDIT,
    AuthScope.WHISPERS_READ,
]

MOCK_SCOPES = [
    AuthScope.BITS_READ,
    AuthScope.CHANNEL_MANAGE_POLLS,
    AuthScope.CHANNEL_MANAGE_POLLS,
    AuthScope.CHANNEL_MANAGE_POLLS,
    AuthScope.CHANNEL_MANAGE_PREDICTIONS,
    AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
    AuthScope.CHANNEL_READ_CHARITY,
    AuthScope.CHANNEL_READ_GOALS,
    AuthScope.CHANNEL_READ_HYPE_TRAIN,
    AuthScope.CHANNEL_READ_HYPE_TRAIN,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.MODERATOR_MANAGE_SHOUTOUTS,
    AuthScope.USER_READ_FOLLOWS,
]


class TwitchAPI:
    def __init__(self, client_id, client_secret, test_mode=False):
        """Initialize the Twitch API client"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.test_mode = test_mode
        self.event_queue = None
        self.auth = TwitchAuth(client_id, client_secret, self.get_scopes(), test_mode)
        self.twitch = None
        self.rewards = TwitchRewards()
        self.eventsub = None
        self.ads = TwitchAds()
        self.chat = TwitchChat()
        self.users = None
        self.is_running = False

    def get_scopes(self):
        """Return the correct scopes based on test mode."""
        return MOCK_SCOPES if self.test_mode else REAL_SCOPES

    async def initialize(self, app):
        """Authenticate and start EventSub WebSocket"""
        self.event_queue = app.state.event_queue

        if not await self.auth.authenticate():
            if not await self.auth.run_codeflow():
                logger.error("❌ Failed authentication, skipping Twitch API startup.")
                return
            if not await self.auth.authenticate():
                logger.error(
                    "❌ Failed authentication (second try), skipping Twitch API startup."
                )
                return

        self.twitch = self.auth.twitch

        self.users = TwitchUsers(self.twitch, self.test_mode)
        await self.users.initialize_badges()

        self.eventsub = TwitchEventSub(
            twitch=self.twitch,
            test_mode=self.test_mode,
            rewards=self.rewards,
            users=self.users,
        )

        await self.eventsub.start_eventsub()
        self.is_running = True

    async def get_stream_info(self):
        """Fetch current Twitch stream details (viewer count, title, etc.)."""
        try:
            user_id = config.TWITCH_CHANNEL_ID  # Use channel ID from config
            stream_generator = self.twitch.get_streams(
                user_id=[user_id]
            )  # This is an async generator

            async for (
                stream_data
            ) in stream_generator:  # Iterate over the async generator
                if stream_data:
                    return stream_data  # First stream object

            return None  # If no stream data is found
        except Exception as e:
            logger.error(f"❌ Error fetching stream info: {e}")
            return None

    async def stop(self):
        """Stops the Twitch API and EventSub WebSocket."""
        if self.is_running:
            logger.info("🛑 Stopping Twitch API and EventSub WebSocket...")

            # Stop EventSub WebSocket
            if hasattr(self, "eventsub") and self.eventsub:
                try:
                    await self.eventsub.stop()
                    logger.info("✅ EventSub WebSocket stopped.")
                except Exception as e:
                    logger.error(f"❌ Error stopping EventSub WebSocket: {e}")

            # Close Twitch API connection
            try:
                if self.twitch:
                    await self.twitch.close()
                    logger.info("✅ Twitch API connection closed.")
            except Exception as e:
                logger.error(f"❌ Error closing Twitch API connection: {e}")

            self.is_running = False
            logger.info("🛑 Twitch API stopped.")
        else:
            logger.info("⚠️ Twitch API was not running.")
