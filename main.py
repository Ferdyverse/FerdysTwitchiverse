#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel, HttpUrl
from typing import Optional
from escpos.printer import Usb
from PIL import Image
import requests
from io import BytesIO
import uvicorn
import logging
import config

# Configure logger
logger = logging.getLogger('uvicorn.error')

printer = None

# Required for Startup and Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global printer
    logger.info("Initializing printer")
    try:
        # Initialize the printer
        printer = Usb(
            config.PRINTER_VENDOR_ID,
            config.PRINTER_PRODUCT_ID,
            timeout=0,
            in_ep=config.PRINTER_IN_EP,
            out_ep=config.PRINTER_OUT_EP,
            profile=config.PRINTER_PROFILE
        )
        logger.info("Printer found!")
        yield  # The printer is available during the app's lifespan
    except Exception as e:
        logger.error(f"Error initializing the printer: {e}")
        yield  # Start the app even if there's an error
    finally:
        # Clean up resources
        if printer is not None:
            try:
                logger.info("Shutting down printer")
                printer.close()
            except Exception as e:
                logger.error(f"Error shutting down the printer: {e}")

# App config
app = FastAPI(
        title="Twitch2HomeLab",
        summary="Get stuff from Twitch to the local network",
        lifespan=lifespan)

class PrintElement(BaseModel):
    type: str  # "headline_1", "headline_2", "image", "message""
    text: str = None
    url: str = None

class PrintRequest(BaseModel):
    print_elements: list[PrintElement]

async def get_image(image_url: str):
    if image_url:
        # Download the image from the URL
        logger.debug("Downloading image!")
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        # Prepare the image (scale and convert)
        image = image.convert("1")  # Convert to black and white
        return image

@app.post("/print")
async def print_data(request: PrintRequest):
    "Prints a json object on my Thermal Printer"
    logger.debug("Request on /print")
    if printer is None:
        logger.error("Printer not available")
        raise HTTPException(status_code=500, detail="Printer not available")

    try:
        logger.debug(request)

        for element in request.print_elements:
            # Headline type 1
            if element.type == "headline_1":
                printer.set(align="center", bold=True, double_height=True)
                printer.text(f"{element.text}\n\n")
            # Headline type 2
            elif element.type == "headline_2":
                printer.set(align="center", bold=True, double_height=False, double_width=True)
                printer.text(f"{element.text}\n\n")
            # Images
            elif element.type == "image":
                pimage = await get_image(element.url)
                if pimage:
                    printer.image(
                        await get_image(element.url),
                        high_density_horizontal=True,
                        high_density_vertical=True,
                        impl="bitImageColumn",
                        fragment_height=960,
                        center=False
                    )
            # Normal Text
            elif element.type == "message":
                # Print message
                printer.set(align="left", normal_textsize=True)
                printer.text(f"{element.text}\n")

        # Cut the paper
        printer.cut()
        return {"status": "success", "message": "Print done!"}

    except requests.RequestException as e:
        logger.error(f"Error downloading the image: {e}")
        raise HTTPException(status_code=400, detail=f"Error downloading the image: {e}")
    except Exception as e:
        logger.error(f"Error printing: {e}")
        raise HTTPException(status_code=500, detail=f"Error printing: {e}")

@app.get("/status")
async def status():
    if printer is None:
        logger.error("Printer is offline")
        return {"status": "online", "printer_state": "Printer not available"}
    return {"status": "online", "printer_state": "Printer ready"}

@app.get('/')
async def home():
    return { "message": "API is running!", "state": "/status", "docs": "/docs" }

if __name__ == '__main__':
    uvicorn.run(
        app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.APP_LOG_LEVEL
    )
