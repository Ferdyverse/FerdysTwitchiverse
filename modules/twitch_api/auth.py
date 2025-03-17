import logging
import config
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, CodeFlow
from modules.misc import save_tokens, load_tokens

logger = logging.getLogger("uvicorn.error.twitch_api_auth")

class TwitchAuth:
    def __init__(self, client_id, client_secret, scopes, test_mode):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.test_mode = test_mode
        self.twitch = None
        self.token = None
        self.refresh_token = None

    async def authenticate(self):
        if self.test_mode:
            logger.info("⚠️ Using Twitch CLI Mock API, skipping real authentication.")
            try:
                self.twitch = await Twitch(self.client_id, self.client_secret, base_url=self.base_url, auth_base_url=self.auth_base_url)
                self.twitch.auto_refresh_auth = False
                auth = UserAuthenticator(self.twitch, self.scopes, auth_base_url=self.auth_base_url)
                self.token = await auth.mock_authenticate(config.TWITCH_CHANNEL_ID)
                await self.twitch.set_user_authentication(self.token, self.scopes)
                logger.info("✅ Successfully authenticated with Twitch Mock API.")
                return True
            except Exception as e:
                logger.error(f"❌ Mock authentication failed: {e}")
                return False

        try:
            logger.info("🔄 API: Checking stored tokens before authentication...")
            tokens = load_tokens("api")
            if tokens:
                self.token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                logger.info("✅ Loaded stored tokens.")

            self.twitch = await Twitch(self.client_id, self.client_secret)

            # Codeflow Auth
            if not self.token or not self.refresh_token:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                await self.run_codeflow()

            try:
                logger.info("Starting user auth...")
                await self.twitch.set_user_authentication(self.token, self.scopes, self.refresh_token)
            except Exception as e:
                logger.warning(f"⚠️ Failed to authenticate with twitch! {e}")
                return False

            app_token = self.twitch.get_app_token()

            self.auth_headers = {
                "Authorization": f"Bearer {app_token}",
                "Client-Id": self.client_id
            }

            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def run_codeflow(self):
        try:
            code_flow = CodeFlow(self.twitch, self.scopes)
            code, url = await code_flow.get_code()
            logger.info(f"📢 Open the following URL to authenticate with twitch (Streamer): {url}")
            token, refresh = await code_flow.wait_for_auth_complete()
            self.token = token
            self.refresh_token = refresh
            save_tokens("api", self.token, self.refresh_token)
            return True
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
