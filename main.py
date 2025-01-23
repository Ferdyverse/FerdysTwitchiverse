#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uvicorn
import logging

from modules.printer_manager import PrinterManager
from modules.schemas import PrintRequest, PrintElement
import config

# Configure logger
logger = logging.getLogger("uvicorn.error")

# Instantiate the PrinterManager
printer_manager = PrinterManager()

# Required for Startup and Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing printer manager")
    try:
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
    title="Twitch2HomeLab",
    summary="Get stuff from Twitch to the local network",
    lifespan=lifespan,
)

@app.post(
    "/print",
    summary="Print Data",
    description="Send data to the thermal printer to print various elements, such as text headlines, messages, or images.",
    response_description="Returns a success message when printing is completed."
)
async def print_data(request: PrintRequest):
    if not printer_manager.is_online():
        printer_manager.reconnect()
        if not printer_manager.is_online():
            raise HTTPException(status_code=500, detail="Printer not available")

    try:
        for element in request.print_elements:
            if await printer_manager.print_element(element):
                printer_manager.newline(1)
        printer_manager.cut_paper()
        return {"status": "success", "message": "Print done!"}
    except Exception as e:
        logger.error(f"Error during printing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/state",
    summary="Get API Status",
    description="Checks the current status of the api."
                "If the printer is offline, an attempt to reconnect will be made.",
    response_description="Returns the current status of the api including whether it is online and its paper status."
)
async def status():
    is_online = printer_manager.is_online()
    return {
        "status": "online",
        "printer": {
            "is_online": is_online,
            "message": "Printer is operational" if is_online else "Printer is offline",
        },
    }

@app.get("/")
async def home():
    return { "docs": "/docs", "state": "/state"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
