import logging
import config
import datetime
import aiohttp
import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.helper import first
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.type import CustomRewardRedemptionStatus

from modules.db_manager import get_db, save_event, save_viewer, Viewer, save_todo

from modules.misc import save_tokens, load_tokens
from modules.websocket_handler import broadcast_message

logger = logging.getLogger("uvicorn.error.twitch_api")

scopes = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.CHANNEL_READ_ADS,
    AuthScope.CHANNEL_MANAGE_BROADCAST,
    AuthScope.CHANNEL_MODERATE,
    AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
    AuthScope.MODERATOR_READ_CHATTERS,
    AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
    AuthScope.MODERATOR_READ_FOLLOWERS,
    AuthScope.MODERATOR_MANAGE_SHOUTOUTS,
    AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
    AuthScope.MODERATION_READ,
    AuthScope.USER_READ_EMAIL,
    AuthScope.USER_READ_FOLLOWS,
    AuthScope.USER_READ_CHAT,
    AuthScope.USER_EDIT_BROADCAST,
    AuthScope.USER_MANAGE_BLOCKED_USERS,
    AuthScope.MODERATOR_MANAGE_BANNED_USERS,
    AuthScope.USER_READ_BLOCKED_USERS,
    AuthScope.BITS_READ,
    AuthScope.CLIPS_EDIT,
    AuthScope.WHISPERS_READ,
    AuthScope.WHISPERS_EDIT,
    AuthScope.ANALYTICS_READ_EXTENSION,
    AuthScope.ANALYTICS_READ_GAMES,
    AuthScope.USER_WRITE_CHAT
]

class TwitchAPI:
    def __init__(self, client_id, client_secret, test_mode=False):
        """Initialize the Twitch API client"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.test_mode = test_mode
        self.event_queue = None
        self.twitch = None
        self.auth = None
        self.auth_headers = None
        self.token = None
        self.refresh_token = None
        self.is_running = False

    async def authenticate(self):
        """Authenticate with Twitch and retrieve access tokens."""

        if self.test_mode:
            logger.info("⚠️ Using Twitch CLI Mock API, skipping authentication.")
            return True

        try:
            logger.info("🔄 Checking stored tokens before authentication...")
            tokens = load_tokens("api")
            if tokens:
                self.token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                logger.info("✅ Loaded stored tokens.")

            self.twitch = await Twitch(self.client_id, self.client_secret)

            app_token = self.twitch.get_app_token()

            self.auth_headers = {
                "Authorization": f"Bearer {app_token}",
                "Client-Id": self.client_id
            }

            global scopes

            if not self.token or not self.refresh_token:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes, force_verify=False, url="http://localhost:17564", host="0.0.0.0", port=17564)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens("api", self.token, self.refresh_token)

            try:
                await self.twitch.set_user_authentication(self.token, scopes, self.refresh_token)
            except:
                logger.warning("⚠️ No valid stored user tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes, force_verify=False, url="http://localhost:17564", host="0.0.0.0", port=17564)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens("api", self.token, self.refresh_token)
                try:
                    await self.twitch.set_user_authentication(self.token, scopes, self.refresh_token)
                except:
                    return False

            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def initialize(self, app):
        """Authenticate and start EventSub WebSocket"""

        self.event_queue = app.state.event_queue

        if not await self.authenticate():
            logger.error("❌ Failed authentication, skipping Twitch API startup.")
            return

        await self.initialize_badges()

        # Start WebSocket EventSub
        await self.start_eventsub()

        self.is_running = True

    async def start_eventsub(self):
        """Initialize WebSocket EventSub and subscribe to events"""
        try:
            self.eventsub = EventSubWebsocket(self.twitch)
            self.eventsub.start()

            user = await first(self.twitch.get_users())  # Get broadcaster ID
            broadcaster_id = user.id

            # Subscribe to Twitch events
            logger.info("Register follow event")
            await self.eventsub.listen_channel_follow_v2(broadcaster_id, broadcaster_id, self.handle_follow)
            logger.info("Register subscribe event")
            await self.eventsub.listen_channel_subscribe(broadcaster_id, self.handle_subscribe)
            logger.info("Register sub gift event")
            await self.eventsub.listen_channel_subscription_gift(broadcaster_id, self.handle_gift_sub)
            logger.info("Register sub msg event")
            await self.eventsub.listen_channel_subscription_message(broadcaster_id, self.handle_sub_message)
            logger.info("Register cheer event")
            await self.eventsub.listen_channel_cheer(broadcaster_id, self.handle_cheer)
            logger.info("Register raid event")
            await self.eventsub.listen_channel_raid(self.handle_raid, None, broadcaster_id)
            logger.info("Register points event")
            await self.eventsub.listen_channel_points_custom_reward_redemption_add(
                broadcaster_id, self.handle_channel_point_redeem
            )
            logger.info("Register ban event")
            await self.eventsub.listen_channel_ban(broadcaster_id, self.handle_ban)
            logger.info("Register unban event")
            await self.eventsub.listen_channel_unban(broadcaster_id, self.handle_mod_action)
            logger.info("Register mod add event")
            await self.eventsub.listen_channel_moderator_add(broadcaster_id, self.handle_mod_action)
            logger.info("Register mod remove event")
            await self.eventsub.listen_channel_moderator_remove(broadcaster_id, self.handle_mod_action)
            logger.info("Register chat clear event")
            await self.eventsub.listen_channel_chat_clear(broadcaster_id, broadcaster_id, self.handle_mod_action)
            logger.info("Register msg delete event")
            await self.eventsub.listen_channel_chat_message_delete(broadcaster_id, broadcaster_id, self.handle_deleted_message)
            logger.info("Register ad break event")
            await self.eventsub.listen_channel_ad_break_begin(broadcaster_id, self.handle_ad_break)

            logger.info("✅ Successfully subscribed to EventSub WebSocket events.")

        except Exception as e:
            logger.error(f"❌ Error initializing EventSub WebSocket: {e}")

    async def handle_follow(self, data: dict):
        """Handle follow event, store user data, and save event."""
        username = data.event.user_name
        user_id = int(data.event.user_id)  # Ensure ID is stored as an integer

        logger.info(f"📢 New follow: {username}")

        # Store viewer data
        save_viewer(
            twitch_id=user_id,
            login=data.event.user_login,
            display_name=username,
            account_type=None,
            broadcaster_type=None,
            profile_image_url="",
            account_age="",
            follower_date=datetime.datetime.utcnow(),
            subscriber_date=None
        )

        # Save event
        save_event("follow", user_id, "")

        # Broadcast event
        await broadcast_message({"alert": {"type": "follower", "user": username, "size": 1}})

    async def handle_subscribe(self, data: dict):
        """Handle subscription event, save it, and broadcast it"""
        username = data.event.user_name
        logger.info(f"🎉 New subscription: {username}")

        save_event("subscription", username, "")

        await broadcast_message({"alert": {"type": "subscriber", "user": username, "size": 1}})

    async def handle_gift_sub(self, data: dict):
        """Handle gift subscription event, save it, and broadcast it"""
        gifter = data.event.user_name
        recipient_count = data.event.total
        logger.info(f"🎁 {gifter} gifted {recipient_count} subs!")

        save_event("gift_sub", gifter, f"Gifted {recipient_count} subs")

        await broadcast_message({"alert": {"type": "gift_sub", "user": gifter, "size": recipient_count}})

    async def handle_sub_message(self, data: dict):
        """Handle subscription messages (e.g., resubs with a custom message)."""
        username = data.event.user_name
        cumulative_months = data.event.cumulative_months
        sub_tier = data.event.tier
        message = data.event.message.text if data.event.message else ""
        user = await first(self.twitch.get_users())
        broadcaster_id = user.id

        logger.info(f"🎉 {username} resubscribed at {sub_tier} for {cumulative_months} months! Message: {message}")

        # Broadcast to overlay
        await broadcast_message({
            "alert": {
                "type": "subscription_message",
                "user": username,
                "tier": sub_tier,
                "months": cumulative_months,
                "message": message
            }
        })

        # Save subscription event in database
        await save_event("subscription_message", int(data["event"]["user_id"]), f"{username} resubbed ({sub_tier}) for {cumulative_months} months. Message: {message}")

    async def handle_raid(self, data: dict):
        """Handle raid event, save it, and broadcast it"""
        username = data.event.from_broadcaster_user_name
        viewer_count = data.event.viewers
        logger.info(f"🚀 Incoming raid from {username} with {viewer_count} viewers!")

        save_event("raid", username, f"Raid with {viewer_count} viewers")

        await broadcast_message({"alert": {"type": "raid", "user": username, "size": viewer_count}})

    async def handle_channel_point_redeem(self, data):
        """Handle channel point redemptions, save them, and broadcast them"""

        logger.info(f"🔄 Received Channel Point Redemption Event: {data}")

        # Extract event attributes
        username = data.event.user_name
        user_id = data.event.user_id
        reward_title = data.event.reward.title
        user_input = data.event.user_input  # Might be empty if not required
        redeem_id = data.event.id # ID of the single redeem
        reward_id = data.event.reward.id # Custom reward ID

        logger.info(f"🎟️ {username} redeemed {reward_title} | Input: {user_input}")

        # Save the event
        save_event("channel_point_redeem", user_id, f"{reward_title}: {user_input}")

        broadcast = True

        if reward_title == "Chatogram":
            await self.event_queue.put({
                "command": "print",
                "user_id": user_id,
                "user": username,
                "message": user_input,
                "redeem_id": redeem_id,
                "reward_id": data.event.reward.id
            })
            broadcast = False
        elif reward_title == "ToDo":
            try:
                todo = save_todo(user_input, user_id)
                if todo:
                    logger.info(todo)
                    await broadcast_message({ "todo": { "action": "create", "id": todo.get("id"), "text": todo.get("text"), "username": todo.get("username") }})
                    await self.twitch.update_redemption_status(config.TWITCH_CHANNEL_ID, reward_id, redeem_id, CustomRewardRedemptionStatus.FULFILLED)
                else:
                    await self.twitch.update_redemption_status(config.TWITCH_CHANNEL_ID, reward_id, redeem_id, CustomRewardRedemptionStatus.CANCELED)
                broadcast = False
            except:
                logger.error("Todo Error")

        # Broadcast message to overlay/admin panel
        if broadcast:
            await broadcast_message({
                "alert": {
                    "type": "redemption",
                    "user": username,
                    "message": f"{reward_title}: {user_input}"
                }
            })

    async def handle_cheer(self, data: dict):
        """Handle Twitch cheers (bit donations)."""
        username = data.event.user_name
        bits = data.event.bits
        message = data.event.message

        logger.info(f"💎 {username} cheered {bits} bits! Message: {message}")

        # Broadcast the cheer event to the overlay
        await broadcast_message({
            "alert": {
                "type": "cheer",
                "user": username,
                "bits": bits,
                "message": message
            }
        })

        # Save the cheer event in the database
        await save_event("cheer", int(data.event.user_id), f"{username} cheered {bits} bits. Message: {message}")

    async def handle_ban(self, data: dict):
        """Handle ban event"""
        moderator = data.event.moderator_user_name
        target = data.event.user_name
        logger.info(f"🚨 {moderator} banned {target}!")

        save_event("ban", int(data.event.user_id), f"Banned by {moderator}")
        await broadcast_message({"alert": {"type": "ban", "moderator": moderator, "user": target}})

    async def handle_timeout(self, data: dict):
        """Handle timeout (temporary ban)"""
        moderator = data.event.moderator_user_name
        target = data.event.user_name
        duration = data.event.duration
        logger.info(f"⏳ {moderator} timed out {target} for {duration} seconds.")

        save_event("timeout", int(data["event"]["user_id"]), f"Timed out for {duration}s by {moderator}")
        await broadcast_message({"alert": {"type": "timeout", "moderator": moderator, "user": target, "duration": duration}})

    async def handle_mod_action(self, data: dict):
        """Handle moderator actions (deleting messages, enabling slow mode, etc.)"""
        moderator = data["event"]["moderator_user_name"]
        action = data["event"]["action"]
        logger.info(f"🔧 {moderator} performed mod action: {action}")

        save_event("mod_action", None, f"{moderator} performed: {action}")
        await broadcast_message({"alert": {"type": "mod_action", "moderator": moderator, "action": action}})

    async def handle_deleted_message(self, data: dict):
        """Handle deleted messages"""
        target = data.event.user_name
        logger.info(f"🗑️ Message deleted from {target}")

        save_event("message_deleted", int(data.event.user_id), f"Message deleted")
        await broadcast_message({"alert": {"type": "message_deleted", "user": target}})

    async def handle_ad_break(self, data: dict):
        """Handle upcoming ad break notifications from Twitch and save as an event."""
        logger.error(data.event)
        logger.error(vars(data.event))
        ad_length = data.event.duration_seconds  # Ad duration in seconds
        ad_start_time = data.event.started_at  # ISO timestamp for next ad

        logger.info(f"📢 Upcoming ad break! Duration: {ad_length}s | Next ad at: {ad_start_time}")

        # Save ad break as an event in the database
        save_event("ad_break", None, f"Ad break starts in {ad_length}s (Next at {ad_start_time})")

        # Broadcast ad break event with countdown for admin panel
        await broadcast_message({
            "admin_alert": {
                "type": "ad_break",
                "message": f"⏳ Ad break starts soon!",
                "duration": ad_length,
                "start_time": int(time.time())  # Send current timestamp for countdown sync
            }
        })

    async def send_message_as_streamer(self, message: str):
        """
        Sends a message to Twitch chat as the Streamer.
        """
        try:
            await self.twitch.send_chat_message(config.TWITCH_CHANNEL_ID, config.TWITCH_CHANNEL_ID, message)
            logger.info(f"✅ Streamer sent message: {message}")
        except Exception as e:
            logger.error(f"❌ Error sending message as Streamer: {e}")

    async def get_user_info(self, username: str = None, user_id: str = None):
        """Retrieve Twitch user info, including color & badges, and store it in the database"""

        if self.test_mode:
            return self._mock_get_user_info(username)

        if not self.twitch:
            raise Exception("❌ Twitch API not initialized.")

        if not username and not user_id:
            logger.error("❌ get_user_info() called without a username or user_id!")
            return None

        try:
            params = {}
            if username:
                params["logins"] = [username]
            if user_id:
                params["user_ids"] = [user_id]

            users = [user async for user in self.twitch.get_users(**params)]
            if users:
                user = users[0]

                db = next(get_db())

                # Check if user is already in the database
                existing_viewer = db.query(Viewer).filter(Viewer.twitch_id == int(user.id)).first()
                user_color = existing_viewer.color if existing_viewer else None
                user_badges = existing_viewer.badges.split(",") if existing_viewer and existing_viewer.badges else []

                # Fetch color & badges only if missing
                if not user_color:
                    chat_data = await self.get_chat_metadata(user.id)
                    if chat_data:
                        user_color = chat_data.get("color", user_color)

                # Save viewer data to database
                save_viewer(
                    twitch_id=int(user.id),
                    login=user.login,
                    display_name=user.display_name,
                    account_type=user.type,
                    broadcaster_type=user.broadcaster_type,
                    profile_image_url=user.profile_image_url,
                    account_age="",
                    follower_date=None,
                    subscriber_date=None,
                    color=user_color,
                    badges=",".join(user_badges) if user_badges else None
                )

                return {
                    "id": user.id,
                    "login": user.login,
                    "display_name": user.display_name,
                    "type": user.type,
                    "broadcaster_type": user.broadcaster_type,
                    "profile_image_url": user.profile_image_url,
                    "color": user_color,
                    "badges": user_badges
                }

            logger.warning(f"⚠️ No user found for {username or user_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching user info for {username or user_id}: {e}")
            return None
    def _mock_get_user_info(self, username: str):
        """Mock user info for Twitch CLI API."""
        return {
            "id": "123456",
            "login": username,
            "display_name": username.capitalize(),
            "profile_image_url": f"https://mock.twitch.tv/{username}.png",
        }

    async def get_chat_metadata(self, user_id: str):
        """Retrieve Twitch user chat color and badges using the Helix API."""
        try:
            if not self.auth_headers:
                logger.error("❌ get_chat_metadata() called without authentication!")
                return {"color": "#9147FF", "badges": []}  # Use default color if missing auth

            user_color = None

            async with aiohttp.ClientSession() as session:
                # Fetch user chat color
                async with session.get(
                    f"https://api.twitch.tv/helix/chat/color?user_id={user_id}",
                    headers=self.auth_headers
                ) as response:
                    if response.status == 200:
                        color_data = await response.json()
                        if color_data.get("data"):
                            user_color = color_data["data"][0].get("color")
                    else:
                        logger.warning(f"⚠️ Failed to fetch user color: {await response.text()}")

                # Set default color if empty
                user_color = user_color or "#9147FF"  # Twitch default purple

            return {
                "color": user_color
            }

        except Exception as e:
            logger.error(f"❌ Error fetching chat metadata: {e}")
            return {"color": "#9147FF", "badges": []}  # Return safe defaults

    async def get_stream_info(self):
        """Fetch current Twitch stream details (viewer count, title, etc.)."""
        try:
            user_id = config.TWITCH_CHANNEL_ID  # Use channel ID from config
            stream_generator = self.twitch.get_streams(user_id=[user_id])  # This is an async generator

            async for stream_data in stream_generator:  # Iterate over the async generator
                if stream_data:
                    return stream_data  # First stream object

            return None  # If no stream data is found
        except Exception as e:
            logger.error(f"❌ Error fetching stream info: {e}")
            return None

    async def fetch_badge_data(self):
        """Retrieve Twitch Global & Channel Badges and store in a dictionary."""
        badges = {"global": {}, "channel": {}}

        async with aiohttp.ClientSession() as session:
            headers = self.auth_headers  # Ensure your headers contain a valid token

            # Fetch Global Badges
            async with session.get("https://api.twitch.tv/helix/chat/badges/global", headers=headers) as response:
                if response.status == 200:
                    badge_data = await response.json()
                    for badge in badge_data.get("data", []):
                        for version in badge["versions"]:
                            badges["global"][f"{badge['set_id']}/{version['id']}"] = version["image_url_1x"]

            # Fetch Channel Badges
            async with session.get(f"https://api.twitch.tv/helix/chat/badges?broadcaster_id={config.TWITCH_CHANNEL_ID}", headers=headers) as response:
                if response.status == 200:
                    badge_data = await response.json()
                    for badge in badge_data.get("data", []):
                        for version in badge["versions"]:
                            badges["channel"][f"{badge['set_id']}/{version['id']}"] = version["image_url_1x"]

        logger.info(f"✅ Loaded {len(badges['global'])} global badges & {len(badges['channel'])} channel badges")
        return badges

    async def initialize_badges(self):
        """Load badge data on startup."""
        global BADGES
        BADGES = await self.fetch_badge_data()
