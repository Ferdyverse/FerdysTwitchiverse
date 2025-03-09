from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.session import get_db
from database.crud.events import get_recent_events

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/events", tags=["Events"])

@router.get("/", response_class=HTMLResponse)
async def get_events(request: Request, db: AsyncSession = Depends(get_db)):
    """Retrieve the last 50 stored events and return them as an HTML snippet."""
    events = await get_recent_events(db)

    if not events:
        return HTMLResponse("<p class='text-center text-gray-400'>No events yet...</p>")

    return templates.TemplateResponse(
        "includes/events.html",
        {"request": request, "events": events}
    )
