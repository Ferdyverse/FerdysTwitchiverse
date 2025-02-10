import logging
import json
import config
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.helper import first

logger = logging.getLogger("uvicorn.error.twitch")

scopes = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.CHANNEL_MANAGE_BROADCAST,
    AuthScope.MODERATOR_READ_CHATTERS,
    AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
    AuthScope.MODERATOR_READ_FOLLOWERS,
    AuthScope.MODERATOR_MANAGE_SHOUTOUTS,
    AuthScope.USER_READ_EMAIL,
    AuthScope.USER_READ_FOLLOWS,
    AuthScope.USER_EDIT_BROADCAST,
    AuthScope.USER_MANAGE_BLOCKED_USERS,
    AuthScope.USER_READ_BLOCKED_USERS,
    AuthScope.BITS_READ,
    AuthScope.CLIPS_EDIT,
    AuthScope.WHISPERS_READ,
    AuthScope.WHISPERS_EDIT,
    AuthScope.ANALYTICS_READ_EXTENSION,
    AuthScope.ANALYTICS_READ_GAMES,
]

def save_tokens(access_token, refresh_token):
    """Save Twitch tokens to a file."""
    with open(config.TOKEN_FILE, "w") as f:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)


def load_tokens():
    """Load Twitch tokens from a file."""
    try:
        with open(config.TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

class TwitchAPI:
    def __init__(self, client_id, client_secret):
        """Initialize the Twitch API client"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_url = config.TWITCH_REDIRECT_URL
        self.twitch = None
        self.auth = None
        self.is_running = False

    async def authenticate(self):
        """Authenticate with Twitch and retrieve access tokens."""
        try:
            logger.info("🔄 Checking stored tokens before authentication...")
            tokens = load_tokens()
            if tokens:
                self.token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                logger.info("✅ Loaded stored tokens.")

            self.twitch = await Twitch(self.client_id, self.client_secret)

            global scopes

            if not self.token or not self.refresh_token:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes, force_verify=False, url=self.redirect_url)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens(self.token, self.refresh_token)

            try:
                await self.twitch.set_user_authentication(self.token, scopes, self.refresh_token)
            except:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes, force_verify=False, url=self.redirect_url)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens(self.token, self.refresh_token)
                return False

            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def initialize(self):
        """Authenticate with Twitch API"""
        if not await self.authenticate():
            logger.error("❌ Failed authentication, skipping twitch api startup.")
            return
        else:
            self.is_running = True

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
