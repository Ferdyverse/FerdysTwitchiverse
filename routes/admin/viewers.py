from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from modules.db_manager import get_db, ChatMessage
import config
import logging

logger = logging.getLogger("uvicorn.error.viewers")

router = APIRouter(prefix="/viewers", tags=["Viewers"])

@router.delete("/delete-message/{message_id}")
async def delete_chat_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a chat message from Twitch and the database."""
    twitch_api = request.app.state.twitch_api
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        await twitch_api.twitch.delete_chat_message(config.TWITCH_CHANNEL_ID, message.viewer_id, message_id)
        db.delete(message)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete Twitch chat message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete message.")
