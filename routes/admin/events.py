from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from modules.db_manager import get_recent_events

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/events", tags=["Events"])

@router.get("/", response_class=HTMLResponse)
async def get_events():
    """
    Retrieve the last 50 stored events and return them as an HTML snippet.
    """
    events = get_recent_events()

    if not events:
        return "<p class='text-center text-gray-400'>No events yet...</p>"

    event_html = ""

    for event in reversed(events):
        event_type = event.event_type.replace("_", " ").capitalize()
        username = event.username if event.username else "Unknown"
        timestamp = event.timestamp.strftime('%d.%m.%Y %H:%M:%S')

        if "admin_action" in event.event_type:
            color_class = "border-blue-500 bg-blue-900/20"
        elif "button_click" in event.event_type:
            color_class = "border-yellow-500 bg-yellow-900/20"
        elif "function_call" in event.event_type:
            color_class = "border-green-500 bg-green-900/20"
        elif "error" in event.event_type:
            color_class = "border-red-500 bg-red-900/20"
        elif "channel_point" in event.event_type:
            color_class = "border-lime-500 bg-lime-900/20"
        else:
            color_class = "border-gray-500 bg-gray-800"

        # **EXACT format as you requested**
        event_html += f"""
            <div class="p-3 mb-2 rounded-md shadow-md border-l-4 {color_class}">
                <!-- First Line: Action (Bold) -->
                <div class="font-semibold text-white">{event_type}</div>

                <!-- Second Line: Date (Small) -->
                <div class="text-xs text-gray-400">{timestamp}</div>

                <!-- Third Line: Details -->
                <div class="mt-2 text-gray-300 text-sm">{event.message}</div>

                <!-- Fourth Line: Username (Yellow, Small) -->
                <div class="mt-1 text-xs text-yellow-400 font-semibold">{username}</div>
            </div>
        """

    return HTMLResponse(content=event_html)
