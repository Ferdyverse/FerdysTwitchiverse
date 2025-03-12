import logging
from modules.twitch_api import (
    TwitchAuth,
    TwitchEventSub,
    TwitchChat,
    TwitchUsers,
    TwitchRewards,
    TwitchModeration,
    TwitchAds
)

logger = logging.getLogger("uvicorn.error.twitch_api")

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
        self.twitch = None
        self.auth = TwitchAuth(client_id, client_secret, self.get_scopes(), test_mode)
        self.eventsub = TwitchEventSub(self.auth.twitch)
        self.chat = TwitchChat()
        self.users = TwitchUsers()
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
                logger.error("❌ Failed authentication (second try), skipping Twitch API startup.")
                return

        await self.eventsub.start_eventsub()
        self.is_running = True
