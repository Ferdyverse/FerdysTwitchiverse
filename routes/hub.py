import logging
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import re

router = APIRouter(prefix="/hub", tags=["Hub"])

logger = logging.getLogger("uvicorn.error.hub")

templates = Jinja2Templates(directory="templates")

REGEX = {
    '^(((\W|[pP])(.|r)(r|.)n)|(p.n.{2}|[^cC]r.n))',
    '\w*(?:vulva|vagina|pimmel|penis|pensi|fotze|arsch|p*rn|schwanz|titten|\(*.\))\w*'
}

@router.get("/{text}", response_class=HTMLResponse)
def show_hub(text: str, request: Request):
    """Create a new ToDo linked to a Twitch user."""
    found = ""

    for pattern in REGEX:
        found = re.findall(pattern, text)
        if found != []:
            logger.error(f"Pattern found: {found}")
            text = "Ferdys"

    return templates.TemplateResponse("includes/hub.html", {"request": request, "text": text})
