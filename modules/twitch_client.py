import os
import subprocess
import logging
from twitchAPI.twitch import Twitch

logger = logging.getLogger("uvicorn.error.twitch_client")

class TwitchClient:
    def __init__(self, client_id: str, client_secret: str, test_mode: bool = False):
        self.test_mode = test_mode
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch = None

        if self.test_mode:
            logger.info("⚠️ Running in TEST MODE using Twitch CLI Mock API")
        else:
            logger.info("✅ Running in LIVE MODE with real Twitch API")

    async def initialize(self):
        """Initialize the Twitch API client."""
        if self.test_mode:
            # Twitch CLI mock API does not require authentication
            logger.info("⚠️ Twitch CLI Mock API is active")
        else:
            self.twitch = await Twitch(self.client_id, self.client_secret)
            logger.info("🔑 Twitch API authentication successful")

    async def get_user_info(self, username: str):
        """Retrieve user info from Twitch."""
        if self.test_mode:
            return self._mock_get_user_info(username)
        else:
            users = await self.twitch.get_users(logins=[username])
            return users["data"][0] if users["data"] else None

    async def get_followers(self, broadcaster_id: str):
        """Retrieve follower list."""
        if self.test_mode:
            return self._mock_get_followers()
        else:
            return await self.twitch.get_followers(to_broadcaster_id=broadcaster_id)

    def _mock_get_user_info(self, username: str):
        """Mock user info for test mode."""
        return {
            "id": "123456",
            "login": username,
            "display_name": username.capitalize(),
            "type": "",
            "broadcaster_type": "partner",
            "profile_image_url": f"https://mock.twitch.tv/{username}.png",
        }

    def _mock_get_followers(self):
        """Mock follower list for test mode."""
        return [{"from_id": "789", "from_name": "test_follower", "followed_at": "2025-01-01T00:00:00Z"}]
