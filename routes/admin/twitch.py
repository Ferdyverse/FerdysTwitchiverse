from fastapi import APIRouter, Request, Body
from fastapi.responses import HTMLResponse
from twitchAPI.type import CustomRewardRedemptionStatus
from modules.websocket_handler import broadcast_message
from database.crud.chat import delete_chat_message
from database.crud.events import save_event
import config
import logging
import html

logger = logging.getLogger("uvicorn.error.twitch")
router = APIRouter(prefix="/twitch", tags=["Twitch Integration"])


@router.delete("/delete-message/{message_id}")
async def delete_chat_message_endpoint(message_id: str, request: Request):
    """Delete a chat message from Twitch and the local database (CouchDB)."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return "<p class='text-red-500 text-sm'>❌ Twitch API not initialized!</p>"

    try:
        await twitch_api.delete_message(message_id)
        delete_chat_message(message_id)

        await broadcast_message({"admin_alert": {"type": "chat_update", "message": "Message deleted"}})
        return {"status": "success", "message": "Message deleted"}

    except Exception as e:
        logger.error(f"❌ Error deleting message {message_id}: {e}")
        return {"status": "error", "message": "Failed to delete message"}


@router.post("/reward/create")
async def create_channel_point_reward(request: Request):
    """Create a new Twitch Channel Point Reward and save it to CouchDB."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return {"status": "error", "message": "❌ Twitch API not running"}

    try:
        data = await request.json()
        title = data.get("title")
        cost = data.get("cost")
        prompt = data.get("prompt", "")
        require_input = data.get("require_input", False)

        if not title or not cost:
            return {"status": "error", "message": "⚠️ Title and cost are required."}

        reward = await twitch_api.twitch.create_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            title=title,
            cost=cost,
            prompt=prompt,
            is_enabled=True,
            is_user_input_required=require_input
        )

        logger.info(f"✅ Created new reward: {title} (Cost: {cost})")
        return {"status": "success", "message": f"✅ Reward '{title}' created!"}

    except Exception as e:
        logger.error(f"❌ Failed to create reward: {e}")
        return {"status": "error", "message": "❌ Failed to create reward."}


@router.delete("/reward/delete/{reward_id}")
async def delete_channel_point_reward(request: Request, reward_id: str):
    """Delete a Twitch Channel Point Reward and remove it from CouchDB."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return {"status": "error", "message": "❌ Twitch API not running"}

    try:
        await twitch_api.twitch.delete_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id
        )

        logger.info(f"🗑️ Deleted reward {reward_id}")
        return {"status": "success", "message": "🗑️ Reward deleted."}

    except Exception as e:
        logger.error(f"❌ Failed to delete reward: {e}")
        return {"status": "error", "message": "❌ Failed to delete reward."}

@router.get("/rewards/pending", response_class=HTMLResponse)
async def get_pending_rewards(request: Request):
    """Retrieve all unfulfilled Twitch channel point redemptions."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return "<p class='text-red-500 text-sm'>Twitch API not initialized!</p>"

    try:
        rewards = await get_all_custom_rewards(twitch_api)
        if not rewards:
            return "<p class='text-gray-500 text-sm'>No custom rewards found.</p>"

        redemptions = await get_pending_redemptions(twitch_api, rewards)
        if not redemptions:
            return "<p class='text-gray-500 text-sm'>No pending redemptions.</p>"

        html_output = "<div class='space-y-2'>"
        for redemption in redemptions:
            redeemed_at = redemption.redeemed_at.strftime('%d.%m.%Y %H:%M') if redemption.redeemed_at else "Unknown"

            html_output += f"""
            <div class='p-3 bg-gray-800 border border-gray-700 rounded-md shadow-sm'>
                <div class='font-semibold text-white'>{redemption.reward.title}</div>
                <div class='text-xs text-gray-400'>{redeemed_at}</div>
                <div class='mt-2 text-gray-300 text-sm'>{html.escape(redemption.user_input)}</div>
                <div class='mt-1 text-xs text-yellow-400 font-semibold'>{redemption.user_name}</div>
                <div class='mt-2 flex space-x-2'>
                    <button class='bg-green-500 hover:bg-green-400 text-white px-2 py-1 text-xs rounded'
                            onclick="fulfillRedemption('{redemption.reward.id}', '{redemption.id}')">✔ Fulfill</button>
                    <button class='bg-red-500 hover:bg-red-400 text-white px-2 py-1 text-xs rounded'
                            onclick="cancelRedemption('{redemption.reward.id}', '{redemption.id}')">✖ Refund</button>
                </div>
            </div>
            """
        html_output += "</div>"

        return HTMLResponse(content=html_output)

    except Exception as e:
        logger.error(f"Error fetching pending redemptions: {e}")
        return "<p class='text-red-500 text-sm'>Error fetching pending redemptions.</p>"


async def get_all_custom_rewards(twitch_api):
    """Fetch all custom rewards from Twitch."""
    if not twitch_api:
        return []

    try:
        rewards = await twitch_api.twitch.get_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            only_manageable_rewards=True
        )
        return rewards
    except Exception as e:
        logger.error(f"Failed to fetch custom rewards: {e}")
        return []

async def get_pending_redemptions(twitch_api, rewards):
    """Fetch pending redemptions for each reward."""
    if not twitch_api:
        return []

    try:
        redemptions = []
        for reward in rewards:
            redemptions_generator = twitch_api.twitch.get_custom_reward_redemption(
                broadcaster_id=config.TWITCH_CHANNEL_ID,
                reward_id=reward.id,
                status=CustomRewardRedemptionStatus.UNFULFILLED
            )

            async for redemption in redemptions_generator:
                redemptions.append(redemption)

        return redemptions
    except Exception as e:
        logger.error(f"Failed to fetch pending redemptions: {e}")
        return []

@router.get("/rewards/", response_class=HTMLResponse)
async def get_rewards(request: Request):
    """Fetch and display the existing custom rewards."""
    try:
        twitch_api = request.app.state.twitch_api

        if not twitch_api:
            return "<p class='text-red-500 text-sm'>Twitch API not initialized!</p>"

        rewards = await twitch_api.twitch.get_custom_reward(broadcaster_id=config.TWITCH_CHANNEL_ID)

        if not rewards:
            return "<p class='text-gray-400'>No rewards available.</p>"

        reward_html = "".join(
            f"""
            <div class='bg-gray-800 p-3 rounded-md shadow-md flex justify-between items-center'>
                <div>
                    <p class='text-lg font-bold'>{reward.title}</p>
                    <p class='text-sm text-gray-400'>Cost: {reward.cost} | Requires Input: {"Yes" if reward.is_user_input_required else "No"}</p>
                    <p class='text-sm text-gray-500'>{reward.prompt}</p>
                </div>
                <button class='bg-red-500 px-3 py-1 rounded text-white'
                    onclick="deleteReward('{reward.id}')">🗑️ Delete</button>
            </div>
            """ for reward in rewards
        )

        return reward_html
    except Exception as e:
        logger.error(f"❌ Failed to fetch rewards: {e}")
        return "<p class='text-red-500'>Error fetching rewards.</p>"


async def handle_redemption_update(request: Request, reward_id: str, redeem_id: str, status: CustomRewardRedemptionStatus):
    """Update the status of a Twitch redemption (fulfill/cancel) and save to CouchDB."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return {"status": "error", "message": "❌ Twitch API not running"}

    try:
        await twitch_api.twitch.update_redemption_status(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id,
            redemption_ids=[redeem_id],
            status=status
        )

        logger.info(f"✅ Redemption {redeem_id} updated to {status}")
        return {"status": "success", "message": f"Redemption {status.name.lower()}d"}

    except Exception as e:
        logger.error(f"❌ Failed to update redemption {redeem_id}: {e}")
        return {"status": "error", "message": "Failed to update redemption"}


@router.post("/redemption/fulfill")
async def fulfill_redemption(request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)):
    """Mark a redemption as FULFILLED and store in CouchDB."""
    return await handle_redemption_update(request, reward_id, redeem_id, CustomRewardRedemptionStatus.FULFILLED)


@router.post("/redemption/cancel")
async def cancel_redemption(request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)):
    """Cancel a redemption (refund to the user) and store in CouchDB."""
    return await handle_redemption_update(request, reward_id, redeem_id, CustomRewardRedemptionStatus.CANCELED)


async def save_twitch_event(event_type: str, message: str):
    """Speichert Twitch-Ereignisse (z. B. Redemptions) in CouchDB."""
    save_event(event_type, None, message)
