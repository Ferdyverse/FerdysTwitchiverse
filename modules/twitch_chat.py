import logging
import asyncio
import time
import datetime
import html
import json

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, EventData
from twitchAPI.oauth import CodeFlow
from twitchAPI.type import AuthScope
from modules.twitch_api import TwitchAPI
from modules.misc import save_tokens, load_tokens, replace_emotes
from modules.websocket_handler import broadcast_message
from modules.chat_commands import handle_command

from database.couchdb_client import couchdb_client
from database.crud.viewers import save_viewer, update_viewer_stats
from database.crud.chat import save_chat_message

logger = logging.getLogger("uvicorn.error.twitch_chat")

scopes = [
    AuthScope.CHAT_EDIT,
    AuthScope.CHAT_READ,
    AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
    AuthScope.MODERATOR_READ_CHATTERS,
    AuthScope.USER_WRITE_CHAT,
]


class TwitchChatBot:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        twitch_channel: str,
        twitch_api: TwitchAPI,
        test_mode=False,
    ):
        """Initialize Twitch Chat Bot."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch_channel = twitch_channel
        self.event_queue = None
        self.recent_messages = []
        self.twitch_api = twitch_api
        self.test_mode = test_mode
        self.twitch = None
        self.chat = None
        self.token = None
        self.refresh_token = None
        self.is_running = False

    async def authenticate(self):
        """Authenticate with Twitch and retrieve access tokens."""
        try:
            logger.info("🔄 Bot: Checking stored tokens before authentication...")
            tokens = load_tokens("bot")
            if tokens:
                self.token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                logger.info("✅ Loaded stored tokens.")

            self.twitch = await Twitch(self.client_id, self.client_secret)

            if not self.token or not self.refresh_token:
                logger.warning(
                    "⚠️ No valid stored tokens found. Running full authentication..."
                )
                code_flow = CodeFlow(self.twitch, scopes)
                code, url = await code_flow.get_code()
                logger.info(
                    f"📢 Open the following URL to authenticate with twitch (Bot): {url}"
                )
                token, refresh = await code_flow.wait_for_auth_complete()
                self.token = token
                self.refresh_token = refresh
                save_tokens("bot", self.token, self.refresh_token)

            try:
                await self.twitch.set_user_authentication(
                    self.token, scopes, self.refresh_token
                )
            except:
                logger.warning("⚠️ Failed to authenticate with twitch!")
                return False

            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def start_chat(self, app):
        """Initialize and start Twitch chat bot."""

        if self.test_mode:
            logger.info("⚠️ Running in test mode, skipping real chat connection.")
            return

        self.event_queue = app.state.event_queue

        if not await self.authenticate():
            logger.error("❌ Failed authentication, skipping chat bot startup.")
            return

        try:
            self.chat = await Chat(self.twitch)

            if not self.chat:
                logger.error("❌ Failed to initialize Chat instance!")
                return

            # Register event handlers
            self.chat.register_event(ChatEvent.READY, self.on_ready)
            self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
            self.chat.register_event(ChatEvent.JOIN, self.user_join)

            logger.info("🚀 Starting Twitch chat bot...")
            self.chat.start()

            global BADGES
            BADGES = await self.twitch_api.users.fetch_badge_data()

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

    async def on_message(self, event: EventData):
        """
        Handle incoming chat messages, store in CouchDB,
        and send them to both the overlay and admin panel.
        """

        if self.test_mode:
            logger.info(f"💬 [MOCK] Sending message: {event.text}")
            return

        logger.debug(f"DEBUG: Event Emotes: {json.dumps(event.emotes, indent=2)}")

        username = event.user.display_name
        twitch_id = str(event.user.id)  # Ensure Twitch ID is a string
        message = replace_emotes(html.escape(event.text), event.emotes)
        message_id = event.id
        stream_id = datetime.datetime.utcnow().strftime("%Y%m%d")
        emotes_used = len(event.emotes) if event.emotes else 0
        is_reply = event.reply_parent_user_id is not None  # Check if message is a reply
        is_first = event.first

        # Get CouchDB instances
        chat_db = couchdb_client.get_db("chat")
        viewers_db = couchdb_client.get_db("viewers")

        global BADGES
        user_badges = []
        badge_data = event.user.badges or {}  # Ensure it's a dictionary
        for badge_set, badge_version in badge_data.items():
            badge_key = f"{badge_set}/{badge_version}"
            if badge_key in BADGES["global"]:
                user_badges.append(BADGES["global"][badge_key])
            elif badge_key in BADGES["channel"]:
                user_badges.append(BADGES["channel"][badge_key])
            else:
                logger.warning(f"⚠️ Unknown badge: {badge_key}")

        user_color = None
        avatar_url = "/static/images/default_avatar.png"

        try:
            # Fetch existing user from CouchDB
            existing_user = viewers_db.get(twitch_id)

            if not existing_user:
                # User not found in CouchDB → Fetch from Twitch API
                user_info = await self.twitch_api.users.get_user_info(user_id=twitch_id)

                if user_info:
                    save_viewer(
                        twitch_id=twitch_id,
                        login=user_info.get("login"),
                        display_name=user_info.get("display_name"),
                        profile_image_url=user_info.get("profile_image_url"),
                        color=user_info.get("color"),
                        badges=user_badges,  # Ensure it's stored as a list
                    )
                    user_color = user_info.get("color")
                    avatar_url = user_info.get(
                        "profile_image_url", avatar_url
                    )  # Provide fallback
                else:
                    logger.warning(f"⚠️ Failed to fetch user info for {twitch_id}")
            else:
                # User exists → Update badges only
                save_viewer(twitch_id=twitch_id, badges=user_badges)
                user_color = existing_user.get("color", "#FFFFFF")
                avatar_url = existing_user.get("profile_image_url", avatar_url)

            # Detect and handle !commands
            if message.startswith("!"):
                command_parts = message[1:].split(" ", 1)
                command_name = command_parts[0].lower()
                command_params = command_parts[1] if len(command_parts) > 1 else ""

                await handle_command(self, command_name, command_params, event)

            # Save chat message in CouchDB
            chat_message_doc = {
                "_id": message_id,
                "type": "chat_message",
                "viewer_id": twitch_id,
                "message": message,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "stream_id": stream_id,
            }
            chat_db.save(chat_message_doc)

            # Update viewer stats in CouchDB
            update_viewer_stats(twitch_id, stream_id, message, emotes_used, is_reply)

            # Prepare message for overlay
            if not message.startswith("!"):
                ov_message_id = f"{username}_{int(time.time())}"  # Unique ID
                chat_message = {
                    "id": ov_message_id,
                    "user": username,
                    "message": message,
                    "color": user_color,
                    "badges": user_badges,
                    "avatar": avatar_url,
                }

                # Append message & remove oldest if more than 5 messages
                self.recent_messages.append(chat_message)
                if len(self.recent_messages) > 20:
                    self.recent_messages.pop(0)

                # Send updated chat messages to overlay
                await broadcast_message({"chat": self.recent_messages})

            # Send chat update to admin panel (single latest message)
            admin_chat_message = {
                "admin_chat": {
                    "username": username,
                    "message": message,
                    "avatar": avatar_url,
                    "badges": user_badges,
                    "color": user_color,
                    "message_id": message_id,
                    "is_first": is_first,
                }
            }
            await broadcast_message(admin_chat_message)

        except Exception as e:
            logger.error(f"❌ Error processing chat message: {e}")

    async def send_message(self, message):
        """Send a chat message as the bot."""
        if not self.chat:
            logger.error("❌ Chat instance is not initialized!")
            return

        if not self.is_running:
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
        self.recent_messages = [
            msg for msg in self.recent_messages if msg["id"] != message_id
        ]
        await broadcast_message({"chat": self.recent_messages})

    async def user_join(self, event: EventData):
        logger.info(f"User: {event.user_name} joined the chat!")
