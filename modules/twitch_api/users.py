import logging
import aiohttp
import config
import datetime
from database.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.twitch_api_user")


class TwitchUsers:
    def __init__(self, twitch, test_mode):
        self.twitch = twitch
        self.test_mode = test_mode

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
                doc_id = str(user.id)
                if doc_id in db:
                    existing_viewer = db[doc_id]
                else:
                    existing_viewer = None

                user_color = None
                user_badges = []

                # Check if viewer exists before accessing fields
                if existing_viewer is not None:
                    user_color = existing_viewer.get("color", None)
                    user_badges = existing_viewer.get("badges", "")
                    if not isinstance(user_badges, str):
                        user_badges = ""
                    user_badges = user_badges.split(",")

                # Fetch color & badges only if missing
                if not user_color:
                    chat_data = await self.get_chat_metadata(user.id)
                    if chat_data:
                        user_color = chat_data.get("color", user_color)

                follow_state = await self.get_user_follow_state(user_id=user.id)
                if len(follow_state.data) > 0:
                    follower_date = follow_state.data[0].followed_at.isoformat()
                else:
                    follower_date = None

                account_age = user.created_at.isoformat()

                if existing_viewer is not None:
                    existing_viewer["login"] = user.login
                    existing_viewer["display_name"] = user.display_name
                    existing_viewer["account_type"] = user.type or ""
                    existing_viewer["broadcaster_type"] = user.broadcaster_type or ""
                    existing_viewer["profile_image_url"] = user.profile_image_url or ""
                    existing_viewer["account_age"] = account_age
                    existing_viewer["follower_date"] = follower_date
                    existing_viewer["color"] = user_color
                    existing_viewer["badges"] = (
                        ",".join(user_badges) if user_badges else None
                    )

                    db.save(existing_viewer)

                else:
                    # Ensure no missing values in the document
                    viewer_data = {
                        "_id": doc_id,
                        "login": user.login,
                        "display_name": user.display_name,
                        "account_type": user.type or "",
                        "broadcaster_type": user.broadcaster_type or "",
                        "profile_image_url": user.profile_image_url or "",
                        "account_age": account_age,
                        "follower_date": follower_date,
                        "subscriber_date": None,
                        "color": user_color,
                        "badges": ",".join(user_badges) if user_badges else None,
                    }

                    db[viewer_data["_id"]] = viewer_data  # Create new document

                return {
                    "id": user.id,
                    "login": user.login,
                    "display_name": user.display_name,
                    "type": user.type,
                    "broadcaster_type": user.broadcaster_type,
                    "profile_image_url": user.profile_image_url,
                    "color": user_color,
                    "badges": user_badges,
                }
            else:
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

    async def fetch_badge_data(self):
        """Retrieve Twitch Global & Channel Badges and store in a dictionary."""
        badges = {"global": {}, "channel": {}}

        app_token = self.twitch.get_app_token()

        self.auth_headers = {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": config.TWITCH_CLIENT_ID,
        }

        async with aiohttp.ClientSession() as session:
            headers = self.auth_headers  # Ensure your headers contain a valid token

            # Fetch Global Badges
            async with session.get(
                "https://api.twitch.tv/helix/chat/badges/global", headers=headers
            ) as response:
                if response.status == 200:
                    badge_data = await response.json()
                    for badge in badge_data.get("data", []):
                        for version in badge["versions"]:
                            badges["global"][f"{badge['set_id']}/{version['id']}"] = (
                                version["image_url_1x"]
                            )

            # Fetch Channel Badges
            async with session.get(
                f"https://api.twitch.tv/helix/chat/badges?broadcaster_id={config.TWITCH_CHANNEL_ID}",
                headers=headers,
            ) as response:
                if response.status == 200:
                    badge_data = await response.json()
                    for badge in badge_data.get("data", []):
                        for version in badge["versions"]:
                            badges["channel"][f"{badge['set_id']}/{version['id']}"] = (
                                version["image_url_1x"]
                            )

        logger.info(
            f"✅ Loaded {len(badges['global'])} global badges & {len(badges['channel'])} channel badges"
        )
        return badges

    async def initialize_badges(self):
        """Load badge data on startup."""
        global BADGES
        BADGES = await self.fetch_badge_data()

    async def get_chat_metadata(self, user_id: str):
        """Retrieve Twitch user chat color and badges using the Helix API."""
        try:
            if not self.auth_headers:
                logger.error("❌ get_chat_metadata() called without authentication!")
                return {
                    "color": "#9147FF",
                    "badges": [],
                }  # Use default color if missing auth

            user_color = None

            async with aiohttp.ClientSession() as session:
                # Fetch user chat color
                async with session.get(
                    f"https://api.twitch.tv/helix/chat/color?user_id={user_id}",
                    headers=self.auth_headers,
                ) as response:
                    if response.status == 200:
                        color_data = await response.json()
                        if color_data.get("data"):
                            user_color = color_data["data"][0].get("color")
                    else:
                        logger.warning(
                            f"⚠️ Failed to fetch user color: {await response.text()}"
                        )

                # Set default color if empty
                user_color = user_color or "#9147FF"  # Twitch default purple

            return {"color": user_color}

        except Exception as e:
            logger.error(f"❌ Error fetching chat metadata: {e}")
            return {"color": "#9147FF", "badges": []}  # Return safe defaults

    async def get_user_follow_state(self, user_id):
        try:
            user_data = await self.twitch.get_channel_followers(
                broadcaster_id=config.TWITCH_CHANNEL_ID, user_id=user_id
            )
            return user_data
        except Exception as e:
            return None

    async def ban_user(self, user_id, reason):
        try:
            self.twitch.ban_user(
                config.TWITCH_CHANNEL_ID,
                config.TWITCH_CHANNEL_ID,
                user_id,
                reason,
                duration=None,
            )
        except Exception as e:
            return None

    async def timeout_user(self, user_id, reason, duration):
        try:
            self.twitch.ban_user(
                config.TWITCH_CHANNEL_ID,
                config.TWITCH_CHANNEL_ID,
                user_id,
                reason,
                duration=duration,
            )
        except Exception as e:
            return None
