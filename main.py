#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from escpos.printer import Usb
from PIL import Image, ImageOps
import requests
from io import BytesIO
import logging

# Logger konfigurieren
# logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Twitch2Printer")

# Druckerkonfiguration (Vendor ID und Product ID anpassen!)
# UDEV anpassen nicht vergessen!
VENDOR_ID = 0x0aa7 # WINCOR NIXDORF
PRODUCT_ID = 0x0304 # TH230

# ESCPOS Drucker initialisieren
try:
    printer = Usb(VENDOR_ID, PRODUCT_ID, timeeout=0, in_ep=0x81, out_ep=0x02, profile="TH230")
except Exception as e:
    printer = None
    logger.error(f"Fehler beim Initialisieren des Druckers: {e}")

class PrintRequest(BaseModel):
    image_url: HttpUrl
    headline: str
    twitch_username: str
    message: str

@app.post("/print")
async def print_image(request: PrintRequest):
    if printer is None:
        logger.error("Drucker nicht verfügbar")
        raise HTTPException(status_code=500, detail="Drucker nicht verfügbar")

    try:
        # Bild von der URL herunterladen
        response = requests.get(request.image_url)
        response.raise_for_status()
        logger.info(response)
        image = Image.open(BytesIO(response.content))

        # Überschrift drucken
        printer.set(align="center", bold=True, double_height=True)
        printer.text(f"{request.headline}\n\n")

        # Bild vorbereiten (skalieren und umwandeln)
        image = image.convert("1")  # In Schwarzweiß umwandeln
        #image = ImageOps.invert(image.convert("L"))
        printer.image(image, high_density_horizontal=True, high_density_vertical=True, impl="bitImageColumn", fragment_height=960, center=False)

        # Benutzername unter dem Bild drucken
        printer.set(align="center", bold=True, double_height=False, double_width=True)
        printer.text(f"{request.twitch_username}\n\n")

        # Nachricht drucken
        printer.set(align="left", normal_textsize=True)
        printer.text(f"{request.message}\n")

        # Schneiden
        printer.cut()
        return {"status": "success", "message": "Überschrift, Avatar, Benutzername und Nachricht gedruckt"}

    except requests.RequestException as e:
        logger.error(f"Fehler beim Herunterladen des Bildes: {e}")
        raise HTTPException(status_code=400, detail=f"Fehler beim Herunterladen des Bildes: {e}")
    except Exception as e:
        logger.error(f"Fehler beim Drucken: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Drucken: {e}")

@app.get("/status")
async def status():
    if printer is None:
        logger.error("Drucker ist offline")
        return {"status": "offline", "message": "Drucker nicht verfügbar"}
    return {"status": "online", "message": "Drucker bereit"}
