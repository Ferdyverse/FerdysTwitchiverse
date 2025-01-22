import logging
from escpos.printer import Usb
from PIL import Image
from io import BytesIO
import requests
from modules.schemas import PrintElement  # Import the schema
import config

logger = logging.getLogger("uvicorn.error")

class PrinterManager:
    def __init__(self):
        self.printer = None

    def initialize(self):
        """
        Initialize the USB printer.
        """
        try:
            self.printer = Usb(
                config.PRINTER_VENDOR_ID,
                config.PRINTER_PRODUCT_ID,
                timeout=0,
                in_ep=config.PRINTER_IN_EP,
                out_ep=config.PRINTER_OUT_EP,
                profile=config.PRINTER_PROFILE
            )
            logger.info("Printer initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize the printer: {e}")
            self.printer = None

    def shutdown(self):
        """
        Shut down the printer by closing the connection.
        """
        if self.printer is not None:
            try:
                self.printer.close()
                logger.info("Printer connection closed.")
            except Exception as e:
                logger.error(f"Error shutting down the printer: {e}")

    def reconnect(self):
        """
        Attempt to reconnect the printer.
        """
        logger.info("Attempting to reconnect to the printer...")
        self.initialize()

    def is_online(self):
        """
        Check if the printer is online.
        """
        if self.printer is None:
            return False
        try:
            # Check if the printer is responsive
            return self.printer.is_online()
        except Exception as e:
            logger.error(f"Error checking printer status: {e}")
            return False

    async def get_image(self, image_url: str):
        if not image_url:
            logger.warning("No image URL provided.")
            return None
        try:
            logger.debug(f"Downloading image from {image_url}")
            response = requests.get(image_url, timeout=10)  # Set a timeout
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image = image.convert("1")  # Convert to black and white
            # Scale image to fit printer width (example: 384px for common thermal printers)
            printer_width = 384
            if image.width > printer_width:
                aspect_ratio = printer_width / image.width
                image = image.resize((printer_width, int(image.height * aspect_ratio)))
            logger.debug("Image processed successfully.")
            return image
        except requests.RequestException as e:
            logger.error(f"Error downloading image: {e}")
        except Exception as e:
            logger.error(f"Error processing image: {e}")
        return None

    async def print_element(self, element: PrintElement):
        """
        Print a single element (text or image).
        :param element: A `PrintElement` instance containing the data to print.
        """
        if self.printer is None:
            raise RuntimeError("Printer is not initialized.")

        try:
            if element.type == "headline_1":
                self.printer.set(align="center", bold=True, double_height=True)
                self.printer.text(f"{element.text}\n\n")
                return True
            elif element.type == "headline_2":
                self.printer.set(align="center", bold=True, double_height=False, double_width=True)
                self.printer.text(f"{element.text}\n\n")
                return True
            elif element.type == "image":
                pimage = await self.get_image(element.url)
                if pimage:
                    self.printer.image(
                        pimage,
                        high_density_horizontal=True,
                        high_density_vertical=True,
                        impl="bitImageColumn",
                        fragment_height=960,
                        center=False
                    )
                    return True
            elif element.type == "message":
                self.printer.set(align="left", normal_textsize=True)
                self.printer.text(f"{element.text}\n")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error printing element: {e}")
            raise

    def cut_paper(self):
        """
        Cut the paper.
        """
        if self.printer:
            self.printer.cut()

    def newline(self, count: int):
        """
        Print a newline
        """
        if self.printer:
            self.printer.set(align="left", normal_textsize=True)
            self.printer.ln(count)
