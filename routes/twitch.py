from fastapi import APIRouter, Request, Body
from fastapi.responses import HTMLResponse
import logging
import config

logger = logging.getLogger("uvicorn.error.routes.twitch")
router = APIRouter(prefix="/twitch", tags=["Twitch Integration"])


@router.get("/rewards", response_class=HTMLResponse)
async def get_rewards(request: Request):
    """Fetch and display existing Twitch rewards."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api.is_running:
        return "<p class='text-red-500 text-sm'>Twitch API not initialized!</p>"

    try:
        rewards = await twitch_api.twitch.get_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID
        )
        return rewards or "<p class='text-gray-400'>No rewards available.</p>"
    except Exception as e:
        logger.error(f"❌ Failed to fetch rewards: {e}")
        return "<p class='text-red-500'>Error fetching rewards.</p>"


@router.post("/create-reward/")
async def create_channel_point_reward(request: Request):
    """Create a new custom channel point reward."""
    twitch_api = request.app.state.twitch_api
    data = await request.json()

    if not twitch_api.is_running:
        return {"status": "error", "message": "Twitch API not initialized"}

    title, cost = data.get("title"), data.get("cost")

    if not title or not cost:
        return {"status": "error", "message": "Title and cost are required."}

    try:
        await twitch_api.twitch.create_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            title=title,
            cost=cost,
            is_enabled=True,
        )
        return {"status": "success", "message": f"Reward '{title}' created!"}
    except Exception as e:
        logger.error(f"❌ Failed to create reward: {e}")
        return {"status": "error", "message": "Failed to create reward."}
