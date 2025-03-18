from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import datetime

import logging

logger = logging.getLogger("uvicorn.error.stream")

router = APIRouter(prefix="/stream", tags=["Stream Stats"])

@router.get("/state", response_class=HTMLResponse)
async def get_viewer_count(request: Request):
    """Retrieve the current Twitch viewer count and return it as an HTML snippet."""
    twitch_api = request.app.state.twitch_api  # Ensure Twitch API is initialized

    if not twitch_api or not twitch_api.is_running:
        return "<span class='text-red-500'>N/A</span>"

    try:
        stream_info = await twitch_api.get_stream_info()

        if not stream_info:
            return "<p class='text-red-500 font-bold'>🔴 Offline</p>"
        else:
            if stream_info.type == "live":
                stream_duration = datetime.datetime.now(datetime.timezone.utc) - stream_info.started_at
                stream_duration = stream_duration.total_seconds()
                return f"<p class='text-green-400 font-bold'>🟢 Online</p><p>{stream_duration}</p>"

    except Exception as e:
        logger.error(f"❌ Error fetching viewer count: {e}")
        return "<span class='text-red-500'>N/A</span>"
