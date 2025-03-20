from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database.crud.events import get_recent_events

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/", response_class=HTMLResponse)
async def get_events():
    """Retrieve the last 50 stored events and return them as HTML."""
    events = get_recent_events()

    if not events:
        return "<p class='text-center text-gray-400'>No events yet...</p>"

    return templates.TemplateResponse(
        "includes/events.html", {"request": {}, "events": events}
    )
