import logging
import config
import datetime
import aiohttp
import pytz
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, CodeFlow
from twitchAPI.type import AuthScope
from twitchAPI.helper import first
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.type import CustomRewardRedemptionStatus

from modules.couchdb_client import couchdb_client
from database.crud.overlay import save_overlay_data
from database.crud.todos import save_todo
from database.crud.events import save_event
from database.crud.viewers import save_viewer

from modules.misc import save_tokens, load_tokens
from modules.websocket_handler import broadcast_message

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
        self.auth = None
        self.auth_headers = None
        self.token = None
        self.refresh_token = None
        self.scopes = MOCK_SCOPES if self.test_mode else REAL_SCOPES
        self.is_running = False

        if self.test_mode:
            logger.warning("⚠️ Running in Twitch Mock API mode!")
            self.base_url = "http://localhost:8080/mock/"
            self.auth_base_url = "http://localhost:8080/auth/"
            self.websocket_url = "ws://127.0.0.1:8081/ws"
            self.subscription_url = "http://127.0.0.1:8081/"
        else:
            self.base_url = "https://api.twitch.tv/helix"
            self.auth_base_url = "https://id.twitch.tv/oauth2"

    async def authenticate(self):
        """Authenticate with Twitch and retrieve access tokens."""

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
            logger.info("🔄 Checking stored tokens before authentication...")
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

    async def initialize(self, app):
        """Authenticate and start EventSub WebSocket"""

        self.event_queue = app.state.event_queue

        if not await self.authenticate():
            logger.warning("❌ First auth failed! Running CodeFlow!")
            if not await self.run_codeflow():
                logger.error("❌ Failed authentication, skipping Twitch API startup.")
                return
            else:
                if not await self.authenticate():
                    logger.error("❌ Failed authentication (second try), skipping Twitch API startup.")
                    return

        await self.initialize_badges()

        # Start WebSocket EventSub
        await self.start_eventsub()

        self.is_running = True

    async def stop(self):
        """Stops the Twitch API and EventSub WebSocket."""
        if self.is_running:
            logger.info("🛑 Stopping Twitch API and EventSub WebSocket...")

            # Stop EventSub WebSocket
            if hasattr(self, "eventsub") and self.eventsub:
                try:
                    await self.eventsub.stop()
                    logger.info("✅ EventSub WebSocket stopped.")
                except Exception as e:
                    logger.error(f"❌ Error stopping EventSub WebSocket: {e}")

            # Close Twitch API connection
            try:
                if self.twitch:
                    await self.twitch.close()
                    logger.info("✅ Twitch API connection closed.")
            except Exception as e:
                logger.error(f"❌ Error closing Twitch API connection: {e}")

            self.is_running = False
            logger.info("🛑 Twitch API stopped.")
        else:
            logger.info("⚠️ Twitch API was not running.")


    async def start_eventsub(self):
        """Initialize WebSocket EventSub and subscribe to events"""
        try:
            self.eventsub = EventSubWebsocket(self.twitch,
                                                connection_url=self.websocket_url if self.test_mode else None,
                                                subscription_url=self.subscription_url if self.test_mode else None)
            self.eventsub.start()

            user = await first(self.twitch.get_users())  # Get broadcaster ID
            broadcaster_id = user.id

            endpoints = []
            # Subscribe to Twitch events
            logger.info("Register follow event")
            event_id = await self.eventsub.listen_channel_follow_v2(broadcaster_id, broadcaster_id, self.handle_follow)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.follow -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register subscribe event")
            event_id = await self.eventsub.listen_channel_subscribe(broadcaster_id, self.handle_subscribe)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.subscribe -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register sub gift event")
            event_id = await self.eventsub.listen_channel_subscription_gift(broadcaster_id, self.handle_gift_sub)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.subscription.gift -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register sub msg event")
            event_id = await self.eventsub.listen_channel_subscription_message(broadcaster_id, self.handle_sub_message)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.subscription.message -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register cheer event")
            event_id = await self.eventsub.listen_channel_cheer(broadcaster_id, self.handle_cheer)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.cheer -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register raid event")
            event_id = await self.eventsub.listen_channel_raid(self.handle_raid, broadcaster_id, None)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.raid -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register points event")
            event_id = await self.eventsub.listen_channel_points_custom_reward_redemption_add(
                broadcaster_id, self.handle_channel_point_redeem
            )
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.channel_points_custom_reward_redemption.add -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register ban event")
            event_id = await self.eventsub.listen_channel_ban(broadcaster_id, self.handle_ban)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.ban -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register unban event")
            event_id = await self.eventsub.listen_channel_unban(broadcaster_id, self.handle_mod_action)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.unban -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register mod add event")
            event_id = await self.eventsub.listen_channel_moderator_add(broadcaster_id, self.handle_mod_action)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.moderator.add -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register mod remove event")
            event_id = await self.eventsub.listen_channel_moderator_remove(broadcaster_id, self.handle_mod_action)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.moderator.remove -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')
            logger.info("Register mod event")
            event_id = await self.eventsub.listen_channel_moderate(broadcaster_id, broadcaster_id ,self.handle_mod_action)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.moderate -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')

            if not self.test_mode:
                logger.info("Register automod event")
                await self.eventsub.listen_automod_message_hold(broadcaster_id, broadcaster_id, self.handle_automod_action)
                logger.info("Register chat clear event")
                await self.eventsub.listen_channel_chat_clear(broadcaster_id, broadcaster_id, self.handle_mod_action)
                logger.info("Register msg delete event")
                await self.eventsub.listen_channel_chat_message_delete(broadcaster_id, broadcaster_id, self.handle_deleted_message)
            logger.info("Register ad break event")
            event_id = await self.eventsub.listen_channel_ad_break_begin(broadcaster_id, self.handle_ad_break)
            if self.test_mode: endpoints.append(f'twitch-cli event trigger channel.ad_break.begin -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket')

            logger.info("✅ Successfully subscribed to EventSub WebSocket events.")

            if self.test_mode:
                with open("commands.md", "w") as cmd_file:
                    for command in endpoints:
                        cmd_file.write(f"{command}\n\n")
                logger.info(f'🔧 The current commandlist can be found in the commands.md file')

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
            follower_date=datetime.datetime.now(datetime.timezone.utc)
        )

        # Save event
        save_event("follow", user_id, "")

        if not self.test_mode:
            save_overlay_data("last_follower", username)

        # Broadcast event
        await broadcast_message({"alert": {"type": "follower", "user": username, "size": 1}})

    async def handle_subscribe(self, data: dict):
        """Handle subscription event, save it, and broadcast it."""
        username = data.event.user_name
        user_id = int(data.event.user_id)
        logger.info(f"🎉 New subscription: {username}")

        # Store viewer data
        await save_viewer(
            twitch_id=user_id,
            login=data.event.user_login,
            display_name=username,
            subscriber_date=datetime.datetime.now(datetime.timezone.utc)
        )

        # Save event
        save_event("subscription", user_id, f"Tier: {data.event.tier}\n\nGift: {data.event.is_gift}")

        if not self.test_mode:
            save_overlay_data("last_subscriber", username)

        # Broadcast event
        await broadcast_message({"alert": {"type": "subscriber", "user": username, "size": 1}})


    async def handle_gift_sub(self, data: dict):
        """Handle gift subscription event, save it, and broadcast it."""
        username = data.event.user_name
        user_id = int(data.event.user_id)
        recipient_count = data.event.total
        logger.info(f"🎁 {username} gifted {recipient_count} subs!")

        if not data.event.is_anonymous:
            await save_viewer(
                twitch_id=user_id,
                login=data.event.user_login,
                display_name=username
            )
        else:
            username = "Anonym"

        save_event("gift_sub", user_id, f"Gifted {recipient_count} subs")

        await broadcast_message({"alert": {"type": "gift_sub", "user": username, "size": recipient_count}})


    async def handle_sub_message(self, data: dict):
        """Handle subscription messages (e.g., resubs with a custom message)."""
        username = data.event.user_name
        user_id = int(data.event.user_id)
        cumulative_months = data.event.cumulative_months
        sub_tier = data.event.tier
        message = data.event.message.text if data.event.message else ""

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
        save_event("subscription_message", user_id, f"{username} resubbed (Tier: {sub_tier}) for {cumulative_months} months. Message: {message}")

        if not self.test_mode:
            save_overlay_data("last_subscriber", username)


    async def handle_raid(self, data: dict):
        """Handle raid event, save it, and broadcast it"""
        username = data.event.from_broadcaster_user_name
        user_id = int(data.event.from_broadcaster_user_id)
        viewer_count = data.event.viewers

        logger.info(f"🚀 Incoming raid from {username} with {viewer_count} viewers!")

        save_viewer(
            twitch_id=user_id,
            login=data.event.from_broadcaster_user_login,
            display_name=username
        )

        save_event("raid", user_id, f"Raid with {viewer_count} viewers")

        await broadcast_message({"alert": {"type": "raid", "user": username, "size": viewer_count}})


    async def handle_channel_point_redeem(self, data):
        """Handle channel point redemptions, save them, and broadcast them"""

        logger.info(f"🔄 Received Channel Point Redemption Event: {data}")

        # Extract event attributes
        username = data.event.user_name
        user_id = int(data.event.user_id)
        reward_title = data.event.reward.title
        user_input = data.event.user_input  # Might be empty if not required
        redeem_id = data.event.id  # ID of the single redeem
        reward_id = data.event.reward.id  # Custom reward ID

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
                "reward_id": reward_id
            })
            broadcast = False

        elif reward_title == "ToDo":
            try:
                todo = save_todo(user_input, user_id)
                if todo:
                    logger.info(todo)
                    await broadcast_message({
                        "todo": {
                            "action": "create",
                            "id": todo.get("id"),
                            "text": todo.get("text"),
                            "username": todo.get("username")
                        }
                    })
                    await self.twitch.update_redemption_status(
                        config.TWITCH_CHANNEL_ID, reward_id, redeem_id, CustomRewardRedemptionStatus.FULFILLED
                    )
                else:
                    await self.twitch.update_redemption_status(
                        config.TWITCH_CHANNEL_ID, reward_id, redeem_id, CustomRewardRedemptionStatus.CANCELED
                    )
                broadcast = False
            except Exception as e:
                logger.error(f"❌ Todo Error: {e}")

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
        save_event("cheer", int(data.event.user_id), f"{username} cheered {bits} bits. Message: {message}")

    async def handle_ban(self, data: dict):
        """Handle ban event"""
        moderator = data.event.moderator_user_name
        target = data.event.user_name
        target_id = int(data.event.user_id)
        reason = data.event.reason

        logger.info(f"🚨 {moderator} banned {target}!")

        save_event("ban", target_id, f"Banned by {moderator} for {reason}")

    async def handle_timeout(self, data: dict):
        """Handle timeout (temporary ban)"""
        moderator = data.event.moderator_user_name
        target = data.event.user_name
        target_id = int(data.event.user_id)
        duration = data.event.duration

        logger.info(f"⏳ {moderator} timed out {target} for {duration} seconds.")

        save_event("timeout", target_id, f"Timed out for {duration}s by {moderator}")

    async def handle_automod_action(self, data: dict):
        """Handle AutoMod actions (message hold, potential flags)."""
        logger.info(vars(data.event))
        logger.info(f"🔧 Automod flagged a message!")

        save_event("mod_action", None, "Automod flagged a message!")

    async def handle_mod_action(self, data: dict):
        """Handle moderator actions (deleting messages, enabling slow mode, etc.)."""
        moderator = data.event.moderator_user_name
        action = data.event.action

        logger.info(f"🔧 {moderator} performed mod action: {action}")

        save_event("mod_action", None, f"{moderator} performed: {action}")

    async def handle_deleted_message(self, data: dict):
        """Handle deleted messages"""
        logger.info(vars(data.event))
        target = data.event.target_user_name
        target_id = int(data.event.target_user_id)

        logger.info(f"🗑️ Message deleted from {target}")

        save_event("message_deleted", target_id, "Message deleted")
        await broadcast_message({"alert": {"type": "message_deleted", "user": target}})


    async def handle_ad_break(self, data: dict):
        """Handle upcoming ad break notifications from Twitch and save as an event."""
        logger.error(data.event)
        logger.error(vars(data.event))
        ad_length = data.event.duration_seconds  # Ad duration in seconds
        ad_start_time = data.event.started_at  # ISO timestamp for next ad

        logger.info(f"📢 Upcoming ad break! Duration: {ad_length}s | Next ad at: {ad_start_time}")

        self.get_ad_schedule()

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
        """Retrieve Twitch user info, including color & badges, and store it in CouchDB."""

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

                # Get CouchDB instance
                db = couchdb_client.get_db("viewers")

                # Fetch existing viewer data (if available)
                existing_viewer = db.get(str(user.id))
                user_color = existing_viewer.get("color") if existing_viewer else None
                user_badges = existing_viewer.get("badges", "").split(",") if existing_viewer else []

                # Fetch color & badges only if missing
                if not user_color:
                    chat_data = await self.get_chat_metadata(user.id)
                    if chat_data:
                        user_color = chat_data.get("color", user_color)

                # Ensure no missing values in the document
                viewer_data = {
                    "_id": str(user.id),
                    "login": user.login,
                    "display_name": user.display_name,
                    "account_type": user.type or "",
                    "broadcaster_type": user.broadcaster_type or "",
                    "profile_image_url": user.profile_image_url or "",
                    "account_age": existing_viewer.get("account_age", ""),
                    "follower_date": existing_viewer.get("follower_date", None),
                    "subscriber_date": existing_viewer.get("subscriber_date", None),
                    "color": user_color,
                    "badges": ",".join(user_badges) if user_badges else None
                }

                # Save or update viewer data in CouchDB
                if existing_viewer:
                    viewer_data["_rev"] = existing_viewer["_rev"]  # Preserve document revision for updates
                    db.save(viewer_data)
                else:
                    db[viewer_data["_id"]] = viewer_data  # Create new document

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

    async def delete_message(self, message_id):
        return await self.twitch.delete_chat_message(config.TWITCH_CHANNEL_ID, config.TWITCH_CHANNEL_ID, message_id)

    async def get_ad_schedule(self):
        """Get the current AD schedule and store the event using the CRUD function."""
        try:
            ads = await self.twitch.get_ad_schedule(config.TWITCH_CHANNEL_ID)

            # Extract relevant ad data
            snooze_count = ads.snooze_count  # Number of available snoozes
            snooze_refresh = ads.snooze_refresh_at  # When snoozes refresh
            next_ad_time = ads.next_ad_at  # When the next ad will play
            duration = ads.duration  # Duration of the next ad (in seconds)
            last_ad = ads.last_ad_at  # Last played ad timestamp (can be None)
            preroll_free_time = ads.preroll_free_time  # Time left without preroll ads (in seconds)

            # Ensure timestamps are in UTC and convert to local timezone
            utc_next_ad_time = next_ad_time.replace(tzinfo=pytz.utc)
            local_next_ad_time = utc_next_ad_time.astimezone(config.LOCAL_TIMEZONE)
            local_next_ad_timestamp = int(local_next_ad_time.timestamp())
            current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

            # Format ad time for logs
            formatted_time = local_next_ad_time.strftime("%H:%M:%S")

            # If next ad is already in the past, return "unknown"
            if (local_next_ad_timestamp - current_timestamp) < 1:
                return {"status": "unknown"}

            save_event(
                event_type="ad_break",
                viewer_id=None,
                message=f"Ad break starts at {formatted_time} for {duration} seconds"
            )

            # Send alert to admin panel
            await broadcast_message({
                "admin_alert": {
                    "type": "ad_break",
                    "duration": duration,
                    "start_time": local_next_ad_timestamp
                }
            })

            logger.info(f"📢 Ad break scheduled at {formatted_time} for {duration} seconds")

            return {"duration": duration, "start_time": local_next_ad_time}

        except Exception as e:
            logger.error(f"❌ Error retrieving ad schedule: {e}")
            return {"status": "error", "message": str(e)}
