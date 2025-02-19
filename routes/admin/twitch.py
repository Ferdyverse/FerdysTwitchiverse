from fastapi import APIRouter, HTTPException, Request, Body
from twitchAPI.type import CustomRewardRedemptionStatus
import config
import logging

logger = logging.getLogger("uvicorn.error.twitch")
router = APIRouter(prefix="/twitch", tags=["Twitch Integration"])

@router.post("/create-reward")
async def create_channel_point_reward(request: Request):
    """Create a new Twitch channel point reward."""
    twitch_api = request.app.state.twitch_api
    data = await request.json()
    title, cost, prompt, require_input = data.get("title"), data.get("cost"), data.get("prompt", ""), data.get("require_input", False)

    if not title or not cost:
        raise HTTPException(status_code=400, detail="Title and cost are required.")

    try:
        await twitch_api.twitch.create_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            title=title,
            cost=cost,
            prompt=prompt,
            is_enabled=True,
            is_user_input_required=require_input
        )
        logger.info(f"✅ Created reward: {title} (Cost: {cost})")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Failed to create reward: {e}")
        raise HTTPException(status_code=500, detail="Failed to create reward.")
