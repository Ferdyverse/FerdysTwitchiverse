import logging
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.twitch_api")

class TwitchUsers:
    async def get_user_info(self, twitch, username=None, user_id=None):
        if not username and not user_id:
            logger.error("❌ get_user_info() called without a username or user_id!")
            return None

        params = {}
        if username:
            params["logins"] = [username]
        if user_id:
            params["user_ids"] = [user_id]

        users = [user async for user in twitch.get_users(**params)]
        if users:
            user = users[0]
            return {
                "id": user.id,
                "login": user.login,
                "display_name": user.display_name,
            }
        return None
