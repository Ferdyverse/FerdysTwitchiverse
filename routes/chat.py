from fastapi import APIRouter, Depends, Form, Response, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.chat import get_recent_chat_messages
import random
import pytz
import config
from modules.twitch_api import TwitchAPI
from modules.twitch_chat import TwitchChatBot

router = APIRouter(prefix="/chat", tags=["Chat"])

# Define the desired local timezone (Change if needed)
LOCAL_TIMEZONE = pytz.timezone("Europe/Berlin")
FALLBACK_COLORS = [
    "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#FF69B4", "#8A2BE2", "#00CED1"
]

@router.get("/", response_class=HTMLResponse)
async def get_chat_messages(db: Session = Depends(get_db)):
    """
    Retrieve the last 50 chat messages from the database, formatted identically to WebSocket messages.
    """
    messages = get_recent_chat_messages(db=db)

    if not messages:
        return "<p class='chat-placeholder text-gray-500 text-center'>No messages yet...</p>"

    chat_html = ""

    for msg in reversed(messages):  # Reverse to show oldest messages first
        username = msg.username or "Unknown"
        avatar_url = msg.avatar or "/static/images/default_avatar.png"
        user_color = msg.user_color or random.choice(FALLBACK_COLORS)

        # Convert timestamp to local timezone
        utc_time = msg.timestamp.replace(tzinfo=pytz.utc)  # Ensure UTC
        local_time = utc_time.astimezone(LOCAL_TIMEZONE).strftime("%H:%M")  # Convert to HH:MM

        # Handle badges (If available)
        badge_html = ""
        if msg.badges:
            badge_list = msg.badges.split(",")  # Convert stored CSV to list
            badge_html = "".join([f'<img src="{badge}" class="chat-badge" alt="badge">' for badge in badge_list])

        important = False
        if msg.message and "!ping" in msg.message.strip().lower():
            important = True

        # HTML structure (Matches WebSocket messages)
        chat_color = "bg-red-400 text-black-600" if important else "bg-gray-900 text-gray-300"
        chat_html += f"""
            <div class="chat-message flex items-start space-x-3 p-3 rounded-md bg-gray-800 border border-gray-700 mb-2 shadow-sm"
                data-message-id="{msg.message_id}" data-user-id="{msg.twitch_id}">
                <img src="{avatar_url}" alt="{username}" class="chat-avatar w-10 h-10 rounded-full border border-gray-600">
                <div class="chat-content flex flex-col w-full">
                    <div class="chat-header flex justify-between items-center text-gray-400 text-sm mb-1">
                        <div class="chat-username font-bold" style="color: {user_color};">{badge_html}{username}</div>
                        <div class="chat-timestamp text-xs">{local_time}</div>
                    </div>
                    <div class="chat-text break-words {chat_color} p-2 rounded-lg w-fit max-w-3xl">
                        {msg.message}
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
            await twitch_api.send_message_as_streamer(message)
        return Response("", media_type="text/html")

    except Exception as e:
        return {"error": f"Failed to send message: {e}"}
