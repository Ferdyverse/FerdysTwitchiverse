import logging
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from modules.websocket_handler import broadcast_message
from database.crud.events import save_event
from database.crud.viewers import save_viewer
from database.crud.overlay import save_overlay_data
import datetime
import config

logger = logging.getLogger("uvicorn.error.twitch_api")


class TwitchEventSub:
    def __init__(self, twitch, rewards, test_mode=False):
        """Initialize the Twitch EventSub handler."""
        self.twitch = twitch
        self.test_mode = test_mode
        self.rewards = rewards
        self.eventsub = None
        self.mock_commands = []  # Stores mock event commands for testing

    async def start_eventsub(self):
        """Initialize the WebSocket EventSub and subscribe to events."""
        try:
            self.eventsub = EventSubWebsocket(
                self.twitch,
                connection_url="ws://127.0.0.1:8081/ws" if self.test_mode else None,
                subscription_url="http://127.0.0.1:8081/" if self.test_mode else None
            )
            self.eventsub.start()

            user = await first(self.twitch.get_users())  # Get broadcaster ID
            broadcaster_id = user.id

            logger.info("🔄 Subscribing to Twitch EventSub events...")

            # Events supported in both real and mock environments
            mock_supported_events = {
                "channel.follow.v2": (broadcaster_id, broadcaster_id, self.handle_follow),
                "channel.subscribe": (broadcaster_id, self.handle_subscribe),
                "channel.subscription.gift": (broadcaster_id, self.handle_gift_sub),
                "channel.subscription.message": (broadcaster_id, self.handle_sub_message),
                "channel.cheer": (broadcaster_id, self.handle_cheer),
                "channel.raid": (self.handle_raid, broadcaster_id, None),
                "channel.channel_points_custom_reward_redemption.add": (broadcaster_id, self.rewards.handle_channel_point_redeem),
                "channel.ban": (broadcaster_id, self.handle_ban),
                "channel.unban": (broadcaster_id, self.handle_mod_action),
                "channel.moderator.add": (broadcaster_id, self.handle_mod_action),
                "channel.moderator.remove": (broadcaster_id, self.handle_mod_action),
                "channel.moderate": (broadcaster_id, broadcaster_id, self.handle_mod_action),
                "channel.ad_break.begin": (broadcaster_id, self.handle_ad_break),
            }

            # Events that are only available in real mode (not in mock testing)
            no_mock_events = {
                "automod.message_hold": (broadcaster_id, broadcaster_id, self.handle_automod_action),
                "channel.chat_clear": (broadcaster_id, broadcaster_id, self.handle_mod_action),
                "channel.chat_message_delete": (broadcaster_id, broadcaster_id, self.handle_deleted_message),
            }

            # Subscribe to all events in real mode
            if not self.test_mode:
                for event, params in {**mock_supported_events, **no_mock_events}.items():
                    await self._subscribe_event(event, *params)

            # Subscribe only to mock-supported events in test mode
            else:
                for event, params in mock_supported_events.items():
                    await self._subscribe_event(event, *params)

                self._write_mock_commands()

            logger.info("✅ Successfully subscribed to all EventSub WebSocket events.")

        except Exception as e:
            logger.error(f"❌ Error initializing EventSub WebSocket: {e}")

    async def _subscribe_event(self, event_name, *params):
        """Helper method to subscribe to an event and register a mock command if applicable."""
        try:
            event_id = await getattr(self.eventsub, f"listen_{event_name.replace('.', '_')}")(*params)

            if self.test_mode:
                mock_command = f"twitch-cli event trigger {event_name} -t {config.TWITCH_CHANNEL_ID} -u {event_id} -T websocket"
                self.mock_commands.append(mock_command)
                logger.info(f"🟡 Registered Mock Event: {mock_command}")

        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {event_name}: {e}")

    def _write_mock_commands(self):
        """Writes all generated mock event commands to a file for easy testing."""
        if not self.mock_commands:
            return  # Avoid creating an unnecessary file

        with open("commands.md", "w") as cmd_file:
            for command in self.mock_commands:
                cmd_file.write(f"{command}\n\n")
        logger.info("📄 The current command list for Mock API can be found in commands.md.")

    # 🟢 EVENT HANDLERS 🟢
    async def handle_follow(self, data: dict):
        """Handle new followers."""
        username = data.event.user_name
        user_id = int(data.event.user_id)
        logger.info(f"📢 New follow: {username}")

        save_viewer(twitch_id=user_id, login=data.event.user_login, display_name=username,
                    follower_date=datetime.datetime.now(datetime.timezone.utc))
        save_event("follow", user_id, "")

        await broadcast_message({"alert": {"type": "follower", "user": username, "size": 1}})

    async def handle_subscribe(self, data: dict):
        """Handle new subscriptions."""
        username = data.event.user_name
        user_id = int(data.event.user_id)
        logger.info(f"🎉 New subscription: {username}")

        await save_viewer(
            twitch_id=user_id,
            login=data.event.user_login,
            display_name=username,
            subscriber_date=datetime.datetime.now(datetime.timezone.utc)
        )

        save_event("subscription", user_id, f"Tier: {data.event.tier}")

        await broadcast_message({"alert": {"type": "subscriber", "user": username, "size": 1}})

    async def handle_gift_sub(self, data: dict):
        """Handle gifted subscriptions."""
        username = data.event.user_name
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

        save_event("gift_sub", int(data.event.user_id), f"Gifted {recipient_count} subs")

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

    async def handle_cheer(self, data: dict):
        """Handle Bit cheers."""
        username = data.event.user_name
        bits = data.event.bits
        logger.info(f"💎 {username} cheered {bits} bits!")

        save_event("cheer", int(data.event.user_id), f"{username} cheered {bits} bits.")
        await broadcast_message({"alert": {"type": "cheer", "user": username, "bits": bits}})

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

    async def handle_mod_action(self, data: dict):
        """Handle moderator actions."""
        moderator = data.event.moderator_user_name
        action = data.event.action
        logger.info(f"🔧 {moderator} performed mod action: {action}")

        save_event("mod_action", None, f"{moderator} performed: {action}")

    async def handle_ad_break(self, data: dict):
        """Handle ad breaks."""
        ad_length = data.event.duration_seconds
        logger.info(f"📢 Upcoming ad break! Duration: {ad_length}s")

        save_event("ad_break", None, f"Ad break scheduled for {ad_length} seconds")
        await broadcast_message({"admin_alert": {"type": "ad_break", "duration": ad_length}})

    async def handle_automod_action(self, data: dict):
        """Handle AutoMod actions (message hold, potential flags)."""
        logger.info(vars(data.event))
        logger.info(f"🔧 Automod flagged a message!")

        save_event("mod_action", None, "Automod flagged a message!")

    async def handle_deleted_message(self, data: dict):
        """Handle deleted messages"""
        logger.info(vars(data.event))
        target = data.event.target_user_name
        target_id = int(data.event.target_user_id)

        logger.info(f"🗑️ Message deleted from {target}")

        save_event("message_deleted", target_id, "Message deleted")
        await broadcast_message({"alert": {"type": "message_deleted", "user": target}})
