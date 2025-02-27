from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter(prefix="/ads", tags=["Ad Break"])

@router.get("/")
async def get_events(request: Request):
    """
    Retrieve the next ad break
    """

    twitch_api = request.app.state.twitch_api

    return await twitch_api.get_ad_schedule()
