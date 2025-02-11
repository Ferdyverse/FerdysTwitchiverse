import logging
import asyncio
import time
import datetime
from modules.db_manager import get_db, save_chat_message, update_viewer_stats, save_viewer
from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, EventData
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from modules.misc import save_tokens, load_tokens
from modules.websocket_handler import broadcast_message

logger = logging.getLogger("uvicorn.error.twitch_chat")

scopes = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.MODERATOR_READ_CHATTERS,
]

class TwitchChatBot:
    def __init__(self, client_id: str, client_secret: str, twitch_channel: str, event_queue: asyncio.Queue):
        """Initialize Twitch Chat Bot."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch_channel = twitch_channel
        self.event_queue = event_queue
        self.recent_messages = []
        self.twitch = None
        self.chat = None
        self.token = None
        self.refresh_token = None
        self.is_running = False

    async def authenticate(self):
        """Authenticate with Twitch and retrieve access tokens."""
        try:
            logger.info("🔄 Checking stored tokens before authentication...")
            tokens = load_tokens("bot")
            if tokens:
                self.token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                logger.info("✅ Loaded stored tokens.")

            self.twitch = await Twitch(self.client_id, self.client_secret)

            if not self.token or not self.refresh_token:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens("bot", self.token, self.refresh_token)

            await self.twitch.set_user_authentication(self.token, scopes, self.refresh_token)
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
            self.chat.register_event(ChatEvent.JOIN, self.user_join)
            # self.chat.register_command("print", self.on_command_print)

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

    async def on_command_print(self, cmd: ChatCommand):
        """Handles the !print command."""
        logger.info(f"CMD parameter: {cmd.parameter}")
        logger.info(f"CMD text: {cmd.text}")

        await self.event_queue.put({
            "command": "print",
            "user_id": cmd.user.id,
            "user": cmd.user.display_name,
            "message": cmd.parameter
        })

    async def on_message(self, event: EventData):
        """
        Handle incoming chat messages from Twitch, store them in the database,
        and send them to both the overlay and admin panel.
        """
        db = next(get_db())
        username = event.user.display_name
        twitch_id = int(event.user.id)  # Ensure Twitch ID is an integer
        message = event.text
        stream_id = "current_stream_id"  # Replace with actual stream tracking logic
        if event.emotes:
            emotes_used = len(event.emotes)  # Count used emotes
        else:
            emotes_used = 0
        is_reply = event.reply_parent_msg_id is not None  # Check if message is a reply

        if event.first:
            # Store viewer data
            save_viewer(
                twitch_id=twitch_id,
                login=event.user.name,
                display_name=username,
                account_type=None,
                broadcaster_type=None,
                profile_image_url="",
                account_age="",
                follower_date=None,
                subscriber_date=None,
                db=db
            )

        # Save chat message in the database
        save_chat_message(twitch_id, message, db)

        # Update viewer stats (both per stream and overall)
        update_viewer_stats(twitch_id, stream_id, message, emotes_used, is_reply, db)

        # Prepare message for overlay
        message_id = f"{username}_{int(time.time())}"  # Unique ID
        chat_message = {
            "id": message_id,
            "user": username,
            "message": message,
            "timestamp": int(time.time()) + 19  # Message disappears after 19s (15s visible + 4s fade-out)
        }

        # Append message & remove oldest if more than 5 messages
        self.recent_messages.append(chat_message)
        if len(self.recent_messages) > 5:
            self.recent_messages.pop(0)

        # Send updated chat messages to overlay
        await broadcast_message({"chat": self.recent_messages})

        # Also send chat update to admin panel (single latest message)
        admin_chat_message = {
            "admin_chat": {
                "username": username,
                "message": message
            }
        }
        await broadcast_message(admin_chat_message)

        # Schedule message removal after 19s
        asyncio.create_task(self.remove_message_after_delay(message_id, 19))

        db.close()

    async def send_message(self, message: str):
        """Send a chat message as the bot."""
        if not self.chat or not self.is_running:
            logger.error("❌ ChatBot is not running, cannot send message.")
            return

        try:
            await self.chat.send_message(self.twitch_channel, message)
            logger.info(f"✅ Bot sent message to chat: {message}")

        except Exception as e:
            logger.error(f"❌ Failed to send chat message: {e}")

    async def remove_message_after_delay(self, message_id, delay):
        """Remove message from list after a delay."""
        await asyncio.sleep(delay)
        self.recent_messages = [msg for msg in self.recent_messages if msg["id"] != message_id]
        await broadcast_message({"chat": self.recent_messages})

    async def user_join(self, event: EventData):
        logger.info(f"User: {event.user_name} joined the chat!")
