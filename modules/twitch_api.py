import logging
import config
import datetime
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.helper import first
from twitchAPI.eventsub.websocket import EventSubWebsocket

from modules.db_manager import get_db, save_event, save_viewer
from sqlalchemy.orm import Session
from fastapi import Depends

from modules.misc import save_tokens, load_tokens
from modules.websocket_handler import broadcast_message

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
            tokens = load_tokens("api")
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
                save_tokens("api", self.token, self.refresh_token)

            try:
                await self.twitch.set_user_authentication(self.token, scopes, self.refresh_token)
            except:
                logger.warning("⚠️ No valid stored tokens found. Running full authentication...")
                auth = UserAuthenticator(self.twitch, scopes, force_verify=False, url=self.redirect_url)
                self.token, self.refresh_token = await auth.authenticate()
                save_tokens("api", self.token, self.refresh_token)
                return False

            logger.info("✅ Twitch authentication successful.")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    async def initialize(self):
        """Authenticate and start EventSub WebSocket"""
        if not await self.authenticate():
            logger.error("❌ Failed authentication, skipping Twitch API startup.")
            return

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
            await self.eventsub.listen_channel_follow(broadcaster_id, self.handle_follow)
            await self.eventsub.listen_channel_subscribe(broadcaster_id, self.handle_subscribe)
            await self.eventsub.listen_channel_subscription_gift(broadcaster_id, self.handle_gift_sub)
            await self.eventsub.listen_channel_subscription_message(broadcaster_id, self.handle_sub_message)
            await self.eventsub.listen_channel_cheer(broadcaster_id, self.handle_cheer)
            await self.eventsub.listen_channel_raid(broadcaster_id, self.handle_raid)
            await self.eventsub.listen_channel_points_custom_reward_redemption_add(
                broadcaster_id, self.handle_channel_point_redeem
            )
            await self.eventsub.listen_channel_ban(broadcaster_id, self.handle_ban)
            await self.eventsub.listen_channel_unban(broadcaster_id, self.handle_mod_action)
            await self.eventsub.listen_channel_moderator_add(broadcaster_id, self.handle_mod_action)
            await self.eventsub.listen_channel_moderator_remove(broadcaster_id, self.handle_mod_action)
            await self.eventsub.listen_channel_chat_clear(broadcaster_id, self.handle_mod_action)
            await self.eventsub.listen_channel_chat_message_delete(broadcaster_id, self.handle_deleted_message)
            await self.eventsub.listen_channel_ad_break(broadcaster_id, self.handle_ad_break)

            logger.info("✅ Successfully subscribed to EventSub WebSocket events.")

        except Exception as e:
            logger.error(f"❌ Error initializing EventSub WebSocket: {e}")

    async def handle_follow(self, data: dict, db: Session = Depends(get_db)):
        """Handle follow event, store user data, and save event."""
        username = data["event"]["user_name"]
        user_id = int(data["event"]["user_id"])  # Ensure ID is stored as an integer

        logger.info(f"📢 New follow: {username}")

        # Store viewer data
        save_viewer(
            twitch_id=user_id,
            login=username,
            display_name=username,
            account_type=None,
            broadcaster_type=None,
            profile_image_url="",
            account_age="",
            follower_date=datetime.datetime.utcnow(),
            subscriber_date=None,
            db=db
        )

        # Save event
        save_event("follow", user_id, "", db)

        # Broadcast event
        await broadcast_message({"alert": {"type": "follower", "user": username, "size": 1}})

    async def handle_subscribe(self, data: dict, db: Session = Depends(get_db)):
        """Handle subscription event, save it, and broadcast it"""
        username = data["event"]["user_name"]
        logger.info(f"🎉 New subscription: {username}")

        save_event("subscription", username, "", db)

        await broadcast_message({"alert": {"type": "subscriber", "user": username, "size": 1}})

    async def handle_gift_sub(self, data: dict, db: Session = Depends(get_db)):
        """Handle gift subscription event, save it, and broadcast it"""
        gifter = data["event"]["user_name"]
        recipient_count = data["event"]["total"]
        logger.info(f"🎁 {gifter} gifted {recipient_count} subs!")

        save_event("gift_sub", gifter, f"Gifted {recipient_count} subs", db)

        await broadcast_message({"alert": {"type": "gift_sub", "user": gifter, "size": recipient_count}})

    async def handle_raid(self, data: dict, db: Session = Depends(get_db)):
        """Handle raid event, save it, and broadcast it"""
        username = data["event"]["from_broadcaster_user_name"]
        viewer_count = data["event"]["viewers"]
        logger.info(f"🚀 Incoming raid from {username} with {viewer_count} viewers!")

        save_event("raid", username, f"Raid with {viewer_count} viewers", db)

        await broadcast_message({"alert": {"type": "raid", "user": username, "size": viewer_count}})

    async def handle_channel_point_redeem(self, data: dict, db: Session = Depends(get_db)):
        """Handle channel point redemptions, save them, and broadcast them"""
        username = data["event"]["user_name"]
        reward_title = data["event"]["reward"]["title"]
        logger.info(f"🎟️ {username} redeemed {reward_title}")

        save_event("channel_point_redeem", username, reward_title, db)

        await broadcast_message({"alert": {"type": "redemption", "user": username, "message": reward_title}})

    async def handle_ban(self, data: dict, db: Session = Depends(get_db)):
        """Handle ban event"""
        moderator = data["event"]["moderator_user_name"]
        target = data["event"]["user_name"]
        logger.info(f"🚨 {moderator} banned {target}!")

        save_event("ban", int(data["event"]["user_id"]), f"Banned by {moderator}", db)
        await broadcast_message({"alert": {"type": "ban", "moderator": moderator, "user": target}})

    async def handle_timeout(self, data: dict, db: Session = Depends(get_db)):
        """Handle timeout (temporary ban)"""
        moderator = data["event"]["moderator_user_name"]
        target = data["event"]["user_name"]
        duration = data["event"]["duration"]
        logger.info(f"⏳ {moderator} timed out {target} for {duration} seconds.")

        save_event("timeout", int(data["event"]["user_id"]), f"Timed out for {duration}s by {moderator}", db)
        await broadcast_message({"alert": {"type": "timeout", "moderator": moderator, "user": target, "duration": duration}})

    async def handle_mod_action(self, data: dict, db: Session = Depends(get_db)):
        """Handle moderator actions (deleting messages, enabling slow mode, etc.)"""
        moderator = data["event"]["moderator_user_name"]
        action = data["event"]["action"]
        logger.info(f"🔧 {moderator} performed mod action: {action}")

        save_event("mod_action", None, f"{moderator} performed: {action}", db)
        await broadcast_message({"alert": {"type": "mod_action", "moderator": moderator, "action": action}})

    async def handle_deleted_message(self, data: dict, db: Session = Depends(get_db)):
        """Handle deleted messages"""
        target = data["event"]["user_name"]
        logger.info(f"🗑️ Message deleted from {target}")

        save_event("message_deleted", int(data["event"]["user_id"]), f"Message deleted", db)
        await broadcast_message({"alert": {"type": "message_deleted", "user": target}})

    async def handle_ad_break(self, data: dict, db: Session = Depends(get_db)):
        """Handle upcoming ad break notifications from Twitch and save as an event."""
        ad_length = data["event"]["length_seconds"]  # Ad duration in seconds
        next_ad_time = data["event"]["next_ad_at"]  # ISO timestamp for next ad
        formatted_time = datetime.datetime.fromisoformat(next_ad_time).strftime("%H:%M:%S")

        logger.info(f"📢 Upcoming ad break! Duration: {ad_length}s | Next ad at: {formatted_time}")

        # Save ad break as an event in the database
        save_event("ad_break", None, f"Ad break starts in {ad_length}s (Next at {formatted_time})", db)

        # Broadcast ad break event with countdown for admin panel
        await broadcast_message({
            "admin_alert": {
                "type": "ad_break",
                "message": f"⏳ Ad break starts soon!",
                "duration": ad_length,
                "start_time": int(time.time())  # Send current timestamp for countdown sync
            }
        })

    async def get_user_info(self, username: str = None, user_id: str = None, db: Session = Depends(get_db)):
        """Retrieve Twitch user info and store it in the database"""

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
                    db=db
                )

                return user

            logger.warning(f"⚠️ No user found for {username or user_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching user info for {username or user_id}: {e}")
            return None
