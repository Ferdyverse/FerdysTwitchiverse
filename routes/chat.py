from fastapi import APIRouter, Depends, Form, Response, Request
from fastapi.responses import HTMLResponse
import random
import pytz
import config
import datetime
import logging
import config

from database.crud.chat import get_recent_chat_messages

router = APIRouter(prefix="/chat", tags=["Chat"])

logger = logging.getLogger("uvicorn.error.routes.chat")

# Define the desired local timezone (Change if needed)
FALLBACK_COLORS = [
    "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#FF69B4", "#8A2BE2", "#00CED1"
]

@router.get("/", response_class=HTMLResponse)
async def get_chat_messages():
    """
    Retrieve the last 50 chat messages from CouchDB, formatted identically to WebSocket messages.
    """
    messages = get_recent_chat_messages()

    if not messages:
        return "<p class='chat-placeholder text-gray-500 text-center'>No messages yet...</p>"

    chat_html = ""

    for msg in reversed(messages):  # Reverse to show oldest messages first
        username = msg.get("username", "Unknown")
        avatar_url = msg.get("avatar", "/static/images/default_avatar.png")
        user_color = msg.get("user_color", random.choice(FALLBACK_COLORS))

        # Convert timestamp to local timezone
        utc_time = msg.get("timestamp")
        if utc_time:
            try:
                # Convert string to datetime (if necessary)
                if isinstance(utc_time, str):
                    utc_time = datetime.datetime.fromisoformat(utc_time)

                # Ensure timezone is UTC before converting
                if utc_time.tzinfo is None:
                    utc_time = pytz.utc.localize(utc_time)

                local_time = utc_time.astimezone(config.LOCAL_TIMEZONE).strftime("%H:%M")  # Convert to HH:MM
            except Exception as e:
                logger.error(f"❌ Failed to process timestamp {utc_time}: {e}")
                local_time = "??:??"
        else:
            local_time = "??:??"

        # Handle badges (If available)
        badge_html = ""
        badges = msg.get("badges", "")
        if badges:
            badge_list = badges.split(",")  # Convert stored CSV to list
            badge_html = "".join([f'<img src="{badge}" class="chat-badge" alt="badge">' for badge in badge_list])

        important = "!ping" in msg.get("message", "").strip().lower()

        # HTML structure (Matches WebSocket messages)
        ping_marker = '<span class="ping-marker mt-1">Ping</span>' if important else ""
        chat_html += f"""
            <div class="chat-message flex items-start space-x-3 p-3 rounded-md bg-gray-800 border border-gray-700 mb-2 shadow-sm"
                data-message-id="{msg.get('_id')}" data-user-id="{msg.get('twitch_id')}">
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
                        {msg.get("message", "")}
                    </div>
                </div>
            </div>
        """

    return HTMLResponse(content=chat_html)

@router.post("/send/")
async def send_chat_message(request: Request,
    message: str = Form(...),
    sender: str = Form("streamer")
):
    """
    Send a chat message from the admin panel as either the Bot or the Streamer.
    """

    twitch_chat = request.app.state.twitch_chat
    twitch_api = request.app.state.twitch_api

    if not message.strip():
        return Response("", media_type="text/html")  # Don't send empty messages

    try:
        if sender == "bot":
            await twitch_chat.send_message(message)
        elif sender == "streamer":
            await twitch_api.chat.send_message_as_streamer(request.app.state.twitch_api.twitch, config.TWITCH_CHANNEL_ID, message)
        return Response("", media_type="text/html")

    except Exception as e:
        return {"error": f"Failed to send message: {e}"}
