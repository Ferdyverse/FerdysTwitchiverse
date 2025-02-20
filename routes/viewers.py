from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.viewers import save_viewer
from modules.websocket_handler import broadcast_message
import logging

logger = logging.getLogger("uvicorn.error.viewers")
router = APIRouter(prefix="/viewers", tags=["Viewers"])

@router.post("/update/{user_id}")
async def update_viewer(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Fetch latest user info and update the viewer database."""
    twitch_api = request.app.state.twitch_api
    if not twitch_api.is_running:
        return "<span class='text-red-500'>N/A</span>"

    try:
        user_info = await twitch_api.get_user_info(user_id=user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        save_viewer(db, twitch_id=user_id, login=user_info["login"], display_name=user_info["display_name"],
                    profile_image_url=user_info["profile_image_url"])

        await broadcast_message({"admin_alert": {"type": "viewer_update", "user_id": user_id}})
        return {"status": "success", "message": "Viewer updated"}
    except Exception as e:
        logger.error(f"❌ Failed to update viewer: {e}")
        raise HTTPException(status_code=500, detail="Failed to update viewer")
