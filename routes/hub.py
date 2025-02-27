from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import logging
import re

router = APIRouter(prefix="/hub", tags=["Hub"])

logger = logging.getLogger("uvicorn.error.hub")

REGEX = [
    r'^(((\W|[pP])(.|r)(r|.)n)|(p.n.{2}|[^cC]r.n))',
    r'\w*(?:vulva|vagina|pimmel|penis|pensi|fotze|arsch|p*rn|schwanz|titten|\(*.\))\w*'
]

@router.get("/{text}", response_class=HTMLResponse)
def show_hub(text: str):
    """Sanitize and filter inappropriate words from text."""

    for pattern in REGEX:
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            logger.warning(f"Pattern found: {found}")
            text = "Ferdys"

    html_content = f"""
    <div class="hub">
        <h1>{text} <span>hub</span></h1>
    </div>
    """
    return HTMLResponse(content=html_content)
