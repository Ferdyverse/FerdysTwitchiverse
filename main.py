#!/usr/bin/env python3

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging
import config

# Import routers
from routes.todo import router as todo_router
from routes.admin import admin_router
from routes.hub import router as hub_router
from routes.overlay import router as overlay_router
from routes.twitch import router as twitch_router
from routes.viewers import router as viewers_router
from routes.chat import router as chat_router
from routes.planets import router as planets_router
from routes.print import router as print_router
from routes.ads import router as ads_router

# Import modules
from modules.websocket_handler import websocket_endpoint
from modules.lifespan import lifespan
from modules.sequence_runner import get_sequence_names

MODULE_COLORS = {
    "twitch_api": "\033[95m",  # Purple
    "twitch_chat": "\033[94m",  # Blue
    "heat_api": "\033[93m",  # Yellow
    "event_queue_processor": "\033[92m",  # Green
    "printer_manager": "\033[96m",  # Cyan
    "uvicorn.error": "\033[91m",  # Red (Uvicorn errors)
    "uvicorn.lifespan": "\033[35m",  # Magenta
    "uvicorn": "\033[90m",  # Dark Gray (General Uvicorn logs)
    "database": "\033[38;5;208m",  # Orange
    "scheduled_messages": "\033[38;5;214m",  # Gold
    "queue_manager": "\033[38;5;33m",  # Deep Blue
}

RESET_COLOR = "\033[0m"

class ColorFormatter(logging.Formatter):
    """Custom formatter to apply colors based on module names only."""

    def format(self, record):
        module_color = MODULE_COLORS.get(record.module, "\033[97m")

        log_message = super().format(record)

        return f"{module_color}{log_message}{RESET_COLOR}"

formatter = ColorFormatter(
    "%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    datefmt=config.APP_LOG_TIME_FORMAT)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
for handler in logging.getLogger("uvicorn").handlers:
    handler.setFormatter(formatter)

templates = Jinja2Templates(directory="templates")

# App Config
app = FastAPI(
    title="Ferdy’s Twitchiverse",
    summary="Get data from Twitch and send it to the local network.",
    description="An API to manage Twitch-related events, overlay updates, and thermal printing.",
    lifespan=lifespan,
    swagger_ui_parameters={"syntaxHighlight.theme": "monokai"}
)

# Include routers
app.include_router(admin_router)
app.include_router(todo_router)
app.include_router(hub_router)
app.include_router(overlay_router)
app.include_router(twitch_router)
app.include_router(viewers_router)
app.include_router(chat_router)
app.include_router(planets_router)
app.include_router(print_router)
app.include_router(ads_router)

# WebSocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get(
    "/",
    summary="API home",
    description="Provides links to the API documentation, overlay, and status endpoints.",
    response_description="Links to API resources.",
    response_class=HTMLResponse)
async def homepage(request: Request):
    """Serve the API Overview Homepage."""
    sequence_names = get_sequence_names()
    return templates.TemplateResponse("homepage.html", {"request": request, "sequence_names": sequence_names})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT, log_level=config.APP_LOG_LEVEL)
