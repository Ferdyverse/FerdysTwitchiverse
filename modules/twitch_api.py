import asyncio
import logging
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first

logger = logging.getLogger("uvicorn.error.twitch")

class TwitchAPI:
    def __init__(self, client_id, client_secret):
        """Initialize the Twitch API client"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch = None

    async def initialize(self):
        """Authenticate with Twitch API"""
        try:
            self.twitch = await Twitch(self.client_id, self.client_secret)
            logger.info("✅ Twitch API initialized successfully.")
        except Exception as e:
            logger.error(f"❌ Error initializing Twitch API: {e}")
            raise

    async def get_user_info(self, username: str):
        """Retrieve Twitch user info"""
        if not self.twitch:
            raise Exception("❌ Twitch API not initialized.")
        try:
            users = await self.twitch.get_users(logins=[username])
            return first(users)
        except Exception as e:
            logger.error(f"❌ Error fetching user info for {username}: {e}")
            return None
