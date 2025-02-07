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

    async def get_user_info(self, username: str = None, user_id: str = None):
        """Retrieve Twitch user info by username or user_id"""

        if not self.twitch:
            raise Exception("❌ Twitch API not initialized.")

        if not username and not user_id:
            logger.error("❌ get_user_info() called without a username or user_id!")
            return None

        try:
            # ✅ Filter out None values before making the API request
            params = {}
            if username:
                params["logins"] = [username]
            if user_id:
                params["user_ids"] = [user_id]

            async for users in self.twitch.get_users(**params):
                return users

        except Exception as e:
            logger.error(f"❌ Error fetching user info for {username or user_id}: {e}")
            return None
