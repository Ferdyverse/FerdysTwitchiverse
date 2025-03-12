from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from modules.websocket_handler import broadcast_message
from database.crud.viewers import save_viewer
import logging

logger = logging.getLogger("uvicorn.error.viewers")

router = APIRouter(prefix="/viewers", tags=["Viewers"])


@router.post("/update/{user_id}")
async def update_viewer(user_id: int, request: Request):
    """Fetch latest user info and update the viewer database (CouchDB)."""

    twitch_api = request.app.state.twitch_api

    if not twitch_api or not twitch_api.is_running:
        return {"status": "error", "message": "Twitch API not initialized"}

    try:
        user_info = await twitch_api.get_user_info(user_id=user_id)

        if not user_info:
            raise HTTPException(status_code=404, detail="User not found in Twitch API")

        # Broadcast update
        await broadcast_message({
            "admin_alert": {"type": "viewer_update", "user_id": user_id, "message": "Viewer info updated"}
        })

        return {"status": "success", "message": "Viewer information updated"}

    except Exception as e:
        logger.error(f"❌ Failed to update viewer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update viewer: {str(e)}")


@router.get("/count", response_class=HTMLResponse)
async def get_viewer_count(request: Request):
    """Retrieve the current Twitch viewer count and return it as an HTML snippet."""
    twitch_api = request.app.state.twitch_api  # Ensure Twitch API is initialized

    if not twitch_api or not twitch_api.is_running:
        return "<span class='text-red-500'>N/A</span>"

    try:
        stream_info = await twitch_api.get_stream_info()

        if not stream_info:
            return "<p class='text-red-500 font-bold'>🔴 Offline</p>"

        viewer_count = stream_info.viewer_count
        return f"<p class='text-green-400 font-bold'>{viewer_count}</p>"

    except Exception as e:
        logger.error(f"❌ Error fetching viewer count: {e}")
        return "<span class='text-red-500'>N/A</span>"
