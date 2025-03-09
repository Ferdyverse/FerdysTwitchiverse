from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.events import get_recent_events
from fastapi.templating import Jinja2Templates
import logging

logger = logging.getLogger("uvicorn.error.events")

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/events", tags=["Events"])

@router.get("/", response_class=HTMLResponse)
async def get_events(request: Request, db: Session = Depends(get_db)):
    """Retrieve the last 50 stored events and return them as HTML."""
    try:
        events = get_recent_events(db=db)

        if not events:
            return HTMLResponse("<p class='text-center text-gray-400'>No events yet...</p>")

        return templates.TemplateResponse("includes/events.html", {"request": request, "events": events})

    except Exception as e:
        logger.error(f"❌ Fehler beim Laden der Events: {e}")
        return HTMLResponse("<p class='text-center text-red-500'>Fehler beim Laden der Events.</p>")
