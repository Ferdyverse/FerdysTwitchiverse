import logging
import config
from twitchAPI.type import CustomRewardRedemptionStatus
from database.crud.events import save_event
from database.crud.todos import save_todo
from modules.websocket_handler import broadcast_message

logger = logging.getLogger("uvicorn.error.twitch_api.rewards")


class TwitchRewards:
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
            await self.event_queue.put(
                {
                    "command": "print",
                    "user_id": user_id,
                    "user": username,
                    "message": user_input,
                    "redeem_id": redeem_id,
                    "reward_id": reward_id,
                }
            )
            broadcast = False

        elif reward_title == "ToDo":
            try:
                todo = save_todo(user_input, user_id, username)
                if todo:
                    logger.info(todo)
                    await broadcast_message(
                        {
                            "todo": {
                                "action": "create",
                                "id": todo.get("id"),
                                "text": todo.get("text"),
                                "username": todo.get("username"),
                            }
                        }
                    )
                    await self.twitch.update_redemption_status(
                        config.TWITCH_CHANNEL_ID,
                        reward_id,
                        redeem_id,
                        CustomRewardRedemptionStatus.FULFILLED,
                    )
                else:
                    await self.twitch.update_redemption_status(
                        config.TWITCH_CHANNEL_ID,
                        reward_id,
                        redeem_id,
                        CustomRewardRedemptionStatus.CANCELED,
                    )
                broadcast = False
            except Exception as e:
                logger.error(f"❌ Todo Error: {e}")

        # Broadcast message to overlay/admin panel
        if broadcast:
            await broadcast_message(
                {
                    "alert": {
                        "type": "redemption",
                        "user": username,
                        "message": f"{reward_title}: {user_input}",
                    }
                }
            )
