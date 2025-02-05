import logging
import asyncio
import json
import requests
import config
from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatMessage, ChatEvent, ChatCommand, EventData, ChatSub
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope

logger = logging.getLogger("uvicorn.error.twitch_chat")

TOKEN_FILE = "twitch_tokens.json"


def save_tokens(access_token, refresh_token):
    """Save Twitch tokens to a file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)


def load_tokens():
    """Load Twitch tokens from a file."""
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


class TwitchChatBot:
    def __init__(self, client_id: str, client_secret: str, twitch_channel: str):
        """Initialize Twitch Chat Bot."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch_channel = twitch_channel
        self.twitch = None
        self.chat = None
        self.token = None
        self.refresh_token = None
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

            if not self.token or not self.refresh_token:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT])
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens(self.token, self.refresh_token)

            await self.twitch.set_user_authentication(self.token, [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT], self.refresh_token)
            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def start_chat(self):
        """Initialize and start Twitch chat bot."""
        if not await self.authenticate():
            logger.error("❌ Failed authentication, skipping chat bot startup.")
            return

        try:
            self.chat = await Chat(self.twitch)

            # Register event handlers
            self.chat.register_event(ChatEvent.READY, self.on_ready)
            self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
            self.chat.register_event(ChatEvent.SUB, self.on_sub)
            self.chat.register_command("print", self.on_command_print)

            logger.info("🚀 Starting Twitch chat bot...")
            self.chat.start()

            self.is_running = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize chat bot: {e}")

    async def stop(self):
        """Stop the Twitch chat bot."""
        if self.chat:
            self.chat.stop()
            self.is_running = False
            logger.info("🛑 Twitch ChatBot stopped.")

    async def on_ready(self, event: EventData):
        """Triggered when the bot is ready."""
        logger.info("✅ Bot is ready, joining channel...")
        await event.chat.join_room(self.twitch_channel)
        logger.info(f"✅ Joined Twitch channel: {self.twitch_channel}")

    async def on_message(self, msg: ChatMessage):
        """Handles incoming chat messages."""
        logger.info(f"💬 {msg.user.name}: {msg.text}")

    async def on_sub(self, sub: ChatSub):
        """Handles new subscriptions."""
        logger.info(f"🎉 New subscription from {sub.user.name}!")

    async def on_command_print(self, cmd: ChatCommand):
        """Handles the !print command."""
        response = f"@{cmd.user.name}, printing your message!"
        await cmd.reply(response)
