from fastapi import APIRouter, Depends, Form, Response, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.crud.chat import get_recent_chat_messages
import random
import pytz
import config
import logging

logger = logging.getLogger("uvicorn.error.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

# Fallback-Farben für User, falls keine gesetzt ist
FALLBACK_COLORS = [
    "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#FF69B4", "#8A2BE2", "#00CED1"
]

@router.get("/", response_class=HTMLResponse)
async def get_chat_messages(db: AsyncSession = Depends(get_db)):
    """
    Retrieve the last 50 chat messages from the database, formatted identically to WebSocket messages.
    """
    try:
        messages = await get_recent_chat_messages(db=db)

        if not messages:
            return HTMLResponse("<p class='chat-placeholder text-gray-500 text-center'>No messages yet...</p>")

        chat_html = ""

        for msg in reversed(messages):  # Reverse to show oldest messages first
            username = msg.username or "Unknown"
            avatar_url = msg.avatar or "/static/images/default_avatar.png"
            user_color = msg.user_color or random.choice(FALLBACK_COLORS)

            # Konvertiere den Timestamp in die lokale Zeitzone
            if msg.timestamp:
                utc_time = msg.timestamp.replace(tzinfo=pytz.utc) if msg.timestamp.tzinfo is None else msg.timestamp
                local_time = utc_time.astimezone(config.LOCAL_TIMEZONE).strftime("%H:%M")
            else:
                local_time = "??:??"

            # Badges verarbeiten
            badge_html = ""
            if msg.badges:
                badge_list = msg.badges.split(",")  # Konvertiere gespeichertes CSV-Format in Liste
                badge_html = "".join([f'<img src="{badge}" class="chat-badge" alt="badge">' for badge in badge_list])

            important = "!ping" in msg.message.strip().lower()

            ping_marker = '<span class="ping-marker mt-1">Ping</span>' if important else ""
            chat_html += f"""
                <div class="chat-message flex items-start space-x-3 p-3 rounded-md bg-gray-800 border border-gray-700 mb-2 shadow-sm"
                    data-message-id="{msg.message_id}" data-user-id="{msg.twitch_id}">
                    <div class="chat-avatar-container flex flex-col items-center justify-center">
                        <img src="{avatar_url}" alt="{username}" class="chat-avatar w-10 h-10 rounded-full border border-gray-600">
                        {ping_marker}
                    </div>
                    <div class="chat-content flex flex-col w-full">
                        <div class="chat-header flex justify-between items-center text-gray-400 text-sm mb-1">
                            <div class="chat-username font-bold" style="color: {user_color};">{badge_html}{username}</div>
                            <div class="chat-timestamp text-xs">{local_time}</div>
                        </div>
                        <div class="chat-text break-words bg-gray-900 text-gray-300 p-2 rounded-lg w-fit max-w-3xl">
                            {msg.message}
                        </div>
                    </div>
                </div>
            """

        return HTMLResponse(content=chat_html)

    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Chat-Nachrichten: {e}")
        return HTMLResponse("<p class='chat-placeholder text-red-500 text-center'>Fehler beim Laden der Nachrichten.</p>")

@router.post("/send/")
async def send_chat_message(
    request: Request,
    message: str = Form(...),
    sender: str = Form("streamer")
):
    """
    Send a chat message from the admin panel as either the Bot or the Streamer.
    """
    twitch_chat = request.app.state.twitch_chat
    twitch_api = request.app.state.twitch_api

    if not message.strip():
        return Response("", media_type="text/html")  # Keine leeren Nachrichten senden

    # Prüfe, ob die Twitch API oder der Chat-Bot laufen
    if sender == "bot" and (not twitch_chat or not twitch_chat.is_running):
        logger.error("❌ Twitch ChatBot ist nicht aktiv!")
        return {"error": "Twitch ChatBot ist nicht aktiv!"}

    if sender == "streamer" and (not twitch_api or not twitch_api.is_running):
        logger.error("❌ Twitch API ist nicht aktiv!")
        return {"error": "Twitch API ist nicht aktiv!"}

    try:
        if sender == "bot":
            await twitch_chat.send_message(message)
        elif sender == "streamer":
            await twitch_api.send_message_as_streamer(message)

        logger.info(f"✅ Nachricht gesendet als {sender}: {message}")
        return Response("", media_type="text/html")

    except Exception as e:
        logger.error(f"❌ Fehler beim Senden der Nachricht: {e}")
        return {"error": f"Failed to send message: {e}"}
