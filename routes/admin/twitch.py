from fastapi import APIRouter, HTTPException, Request, Body, Depends
from twitchAPI.type import CustomRewardRedemptionStatus
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.crud.chat import get_chat_messages, delete_chat_message
from modules.websocket_handler import broadcast_message
import config
import logging
import html

logger = logging.getLogger("uvicorn.error.twitch")
router = APIRouter(prefix="/twitch", tags=["Twitch Integration"])

@router.delete("/delete-message/{message_id}")
async def delete_chat_message_endpoint(
    message_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Delete a chat message from Twitch and the local database."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api or not twitch_api.is_running:
        logger.error("❌ Twitch API not initialized!")
        return {"status": "error", "message": "Twitch API not initialized"}

    try:
        await twitch_api.delete_message(message_id)
        async with db as session:
            await delete_chat_message(message_id, session)

        await broadcast_message({"admin_alert": {"type": "chat_update", "message": "Message deleted"}})
        return {"status": "success", "message": "Message deleted"}

    except Exception as e:
        logger.error(f"❌ Failed to delete message: {e}")
        return {"status": "error", "message": "Failed to delete message"}

@router.post("/pin-message/{message_id}")
async def pin_chat_message_endpoint(
    message_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Pin a chat message in the admin panel."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api or not twitch_api.is_running:
        logger.error("❌ Twitch API not initialized!")
        return {"status": "error", "message": "Twitch API not initialized"}

    try:
        async with db as session:
            message = await get_chat_messages(message_id, session)

        if not message:
            return {"status": "error", "message": "Message not found"}

        await broadcast_message({
            "admin_alert": {
                "type": "chat_pin",
                "message": message["text"],
                "username": message["username"],
            }
        })
        return {"status": "success", "message": "Message pinned"}

    except Exception as e:
        logger.error(f"❌ Failed to pin message: {e}")
        return {"status": "error", "message": "Failed to pin message"}

@router.post("/reward/create")
async def create_channel_point_reward(request: Request):
    try:
        twitch_api = request.app.state.twitch_api
        if not twitch_api or not twitch_api.is_running:
            return {"status": "error", "message": "Twitch API not initialized"}

        data = await request.json()
        title = data.get("title")
        cost = data.get("cost")
        prompt = data.get("prompt", "")
        require_input = data.get("require_input", False)

        if not title or not cost:
            return {"status": "error", "message": "⚠️ Title and cost are required."}

        await twitch_api.twitch.create_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            title=title,
            cost=cost,
            prompt=prompt,
            is_enabled=True,
            is_user_input_required=require_input
        )

        logger.info(f"✅ Created new reward: {title} (Cost: {cost}, Requires Input: {require_input})")
        return {"status": "success", "message": f"✅ Reward '{title}' created!"}

    except Exception as e:
        logger.error(f"❌ Failed to create reward: {e}")
        return {"status": "error", "message": "❌ Failed to create reward"}

@router.delete("/reward/delete/{reward_id}")
async def delete_channel_point_reward(request: Request, reward_id: str):
    try:
        twitch_api = request.app.state.twitch_api

        if not twitch_api or not twitch_api.is_running:
            return {"status": "error", "message": "Twitch API not initialized"}

        await twitch_api.twitch.delete_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id
        )

        logger.info(f"🗑️ Deleted reward {reward_id}")
        return {"status": "success", "message": "🗑️ Reward deleted"}

    except Exception as e:
        logger.error(f"❌ Failed to delete reward: {e}")
        return {"status": "error", "message": "❌ Failed to delete reward"}

@router.post("/redemption/fulfill")
async def fulfill_redemption(
    request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)
):
    """Mark a redemption as FULFILLED."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api or not twitch_api.is_running:
        return {"status": "error", "message": "Twitch API not initialized"}

    try:
        await twitch_api.twitch.update_redemption_status(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id,
            redemption_ids=[redeem_id],
            status=CustomRewardRedemptionStatus.FULFILLED
        )

        logger.info(f"✅ Redemption {redeem_id} marked as fulfilled")
        return {"status": "success", "message": "Redemption fulfilled"}

    except Exception as e:
        logger.error(f"❌ Failed to fulfill redemption: {e}")
        return {"status": "error", "message": "Failed to fulfill redemption"}

@router.post("/redemption/cancel")
async def cancel_redemption(
    request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)
):
    """Cancel a redemption (refund to the user)."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api or not twitch_api.is_running:
        return {"status": "error", "message": "Twitch API not initialized"}

    try:
        await twitch_api.twitch.update_redemption_status(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id,
            redemption_ids=[redeem_id],
            status=CustomRewardRedemptionStatus.CANCELED
        )

        logger.info(f"🚫 Redemption {redeem_id} has been refunded")
        return {"status": "success", "message": "Redemption refunded"}

    except Exception as e:
        logger.error(f"❌ Failed to refund redemption: {e}")
        return {"status": "error", "message": "Failed to refund redemption"}
