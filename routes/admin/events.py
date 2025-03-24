from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from database.crud.events import get_recent_events

templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("uvicorn.error.routes.admin.events")

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/", response_class=HTMLResponse)
def get_events(request: Request):
    """
    Retrieve the last 50 stored events and return them as an HTML snippet.
    """
    events = get_recent_events()

    if not events:
        return "<p class='text-center text-gray-400'>No events yet...</p>"

    return templates.TemplateResponse(
        "includes/events.html", {"request": request, "events": events}
    )
