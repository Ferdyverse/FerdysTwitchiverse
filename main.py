#!/usr/bin/env python3

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi import WebSocket, WebSocketDisconnect, Body

# Other required imports
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Any
import random
import math

# Own modules
from modules.printer_manager import PrinterManager
from modules.schemas import PrintRequest
from modules.db_manager import init_db, save_data, get_data, save_planet, get_planets
import config

# Configure logger
logger = logging.getLogger("uvicorn.error")

# Instantiate the PrinterManager
printer_manager = PrinterManager()

templates = Jinja2Templates(directory="templates")

# Keep track of connected clients
connected_clients = []

# Required for Startup and Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event manager for the FastAPI application.
    Initializes the database and printer manager on startup and shuts them down on exit.
    """
    logger.info("Initializing printer manager")
    try:
        init_db()
        printer_manager.initialize()
        yield  # The app is running
    except Exception as e:
        logger.error(f"Error during lifespan: {e}")
        yield
    finally:
        logger.info("Shutting down printer manager")
        printer_manager.shutdown()

# App config
app = FastAPI(
    title="Ferdy’s Twitchiverse",
    summary="Get data from Twitch and send it to the local network.",
    description="An API to manage Twitch-related events, overlay updates, and thermal printing.",
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai"
    }
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get(
    "/overlay",
    response_class=HTMLResponse,
    summary="Display the overlay",
    description="Serves the HTML page that acts as an overlay for OBS."
)
def overlay(request: Request):
    """
    Endpoint to serve the OBS overlay HTML page.
    """
    return templates.TemplateResponse("overlay.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection to communicate with the frontend overlay in real-time.
    Keeps the connection alive and allows broadcasting data.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Keep the WebSocket connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        connected_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connected_clients.remove(websocket)

async def broadcast_message(message: Any):
    """
    Sends a message to all connected WebSocket clients.
    """
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

@app.post(
    "/send-to-overlay",
    summary="Send data to the overlay",
    description="Accepts data and broadcasts it to all connected WebSocket clients for overlay updates.",
    response_description="Acknowledges the broadcast status."
)
async def send_to_overlay(payload: Any = Body(...)):
    """
    Endpoint to send data to the overlay via WebSocket.
    Saves relevant information to the database for persistence.
    """
    try:
        # Save last follower, subscriber, or raider
        if "alert" in payload:
            alert = payload["alert"]

            # Validate alert data
            if "type" not in alert or "user" not in alert:
                raise HTTPException(status_code=400, detail="Invalid alert data")

            if alert["type"] == "follower":
                save_data("last_follower", alert["user"])
                logger.info(f"Saved last follower: {alert['user']}")

            elif alert["type"] == "subscriber":
                save_data("last_subscriber", alert["user"])
                logger.info(f"Saved last subscriber: {alert['user']}")

            elif alert["type"] == "raid":
                user = alert["user"]
                size = alert.get("size", 0)

                # Generate random angle and distance
                angle = random.uniform(0, 2 * math.pi)  # In radians
                distance = random.uniform(200, 500)

                # Save the planet (raider) to the database
                save_planet(user, size, angle, distance)
                logger.info(f"Planet created for raider {user}: size={size}, angle={angle}, distance={distance}")

        # Broadcast the data to WebSocket clients
        await broadcast_message(payload)
        logger.info("Data broadcasted to overlay")
        return {"status": "success", "message": "Data piped to overlay"}

    except Exception as e:
        logger.error(f"Error piping data: {e}")
        raise HTTPException(status_code=500, detail="Failed to pipe data")

@app.get(
    "/overlay-data",
    summary="Fetch overlay data",
    description="Retrieves the last follower and subscriber from the database.",
    response_description="Returns the last follower and subscriber."
)
async def get_overlay_data():
    """
    Endpoint to fetch the most recent follower and subscriber from the database.
    """
    return {
        "last_follower": get_data("last_follower") or "None",
        "last_subscriber": get_data("last_subscriber") or "None",
    }

@app.post(
    "/print",
    summary="Print data to thermal printer",
    description="Send structured data to the thermal printer for printing.",
    response_description="Returns a success message when printing is completed."
)
async def print_data(request: PrintRequest):
    """
    Endpoint to send data to the thermal printer for printing.
    Validates the printer state and sends the print elements.
    """
    if not printer_manager.is_online():
        printer_manager.reconnect()
        if not printer_manager.is_online():
            raise HTTPException(status_code=500, detail="Printer not available")

    try:
        for element in request.print_elements:
            if await printer_manager.print_element(element):
                printer_manager.newline(1)
        printer_manager.cut_paper(partial=True)
        return {"status": "success", "message": "Print done!"}
    except Exception as e:
        logger.error(f"Error during printing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/state",
    summary="Get API state",
    description="Checks the current status of the API and the printer.",
    response_description="Returns the API and printer status."
)
async def status():
    """
    Endpoint to check the current status of the API and printer.
    Provides details about printer availability and operational status.
    """
    is_online = printer_manager.is_online()
    return {
        "status": "online",
        "printer": {
            "is_online": is_online,
            "message": "Printer is operational" if is_online else "Printer is offline",
        },
    }

@app.get(
    "/solar",
    response_class=HTMLResponse,
    summary="Display the overlay",
    description="Serves the HTML page that acts as an overlay for OBS."
)
def solarsystem(request: Request):
    """
    Endpoint to serve the OBS overlay HTML page.
    """
    return templates.TemplateResponse("solar-system.html", {"request": request})

@app.get(
    "/planets",
    summary="Get all planets (raiders)",
    description="Retrieve all planets in the solar system (saved raids).",
    response_description="Returns a list of planets."
)
async def get_all_planets():
    """
    Fetch all saved planets (raiders) from the database.
    """
    planets = get_planets()  # Replace with your database query to fetch raiders
    return [
        {
            "raider_name": raider_name,
            "raid_size": raid_size,
            "angle": angle,
            "distance": distance
        }
        for raider_name, raid_size, angle, distance in planets
    ]

@app.get(
    "/",
    summary="API home",
    description="Provides links to the API documentation, overlay, and status endpoints.",
    response_description="Links to API resources."
)
async def home():
    """
    Default home endpoint with links to API resources.
    """
    return { "docs": "/docs", "overlay": "/overlay", "state": "/state"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
