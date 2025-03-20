import logging
from escpos.printer import Usb
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
from modules.schemas import PrintElement  # Import the schema
import config
from typing import List, Optional

logger = logging.getLogger("uvicorn.error.printer")


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
                profile=config.PRINTER_PROFILE,
            )
            logger.info("🖨️ Printer module initialized successfully!")
        except Exception as e:
            logger.error(f"🖨️ Failed to initialize the printer module: {e}")
            self.printer = None

    def shutdown(self):
        """
        Shut down the printer by closing the connection.
        """
        if self.printer is not None:
            try:
                self.printer.close()
                logger.info("🖨️ Printer connection closed.")
            except Exception as e:
                logger.error(f"Error shutting down the printer: {e}")

    def reconnect(self):
        """
        Attempt to reconnect the printer.
        """
        logger.info("🖨️ Attempting to reconnect to the printer...")
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
            logger.error(f"🖨️ Error checking printer status: {e}")
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
                self.printer.set(
                    align="center", bold=True, double_height=False, double_width=True
                )
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
                        center=True,
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

    def cut_paper(self, partial: bool = False):
        """
        Cut the paper.
        """
        if self.printer:
            if partial:
                self.printer.cut(mode="PART")
            else:
                self.printer.cut()

    def newline(self, count: int):
        """
        Print a newline
        """
        if self.printer:
            self.printer.set(align="left", normal_textsize=True)
            self.printer.ln(count)

    async def create_image(self, elements: List[PrintElement]) -> Optional[Image.Image]:
        """
        Create a single image that contains all the print elements accumulated.
        :param elements: A list of PrintElement objects to be rendered.
        :return: A PIL Image object with the combined content or None if no elements exist.
        """
        if not elements:
            logger.warning("No elements to create image from.")
            return None

        # Define printer width and spacing settings.
        printer_width = 384
        line_spacing = 10

        # Setup fonts. Attempt to load TrueType fonts, falling back to the default if unavailable.
        try:
            mona = "static/webfonts/MonaspiceRnNerdFontMono-Regular.otf"  # Ensure this is a string.
            noto = "static/webfonts/NotoSansMono-Regular.ttf"
            default_font = ImageFont.truetype(noto, 20)
            headline_font_1 = ImageFont.truetype(mona, 28)
            headline_font_2 = ImageFont.truetype(mona, 26)
        except Exception as e:
            logger.warning("Could not load truetype fonts, falling back to default.")
            default_font = ImageFont.load_default()
            headline_font_1 = default_font
            headline_font_2 = default_font

        # First pass: calculate the total height needed for the final image.
        total_height = 0

        for element in elements:
            if element.type in ["headline_1", "headline_2", "message"]:
                text = element.text or ""
                if element.type == "headline_1":
                    font = headline_font_1
                elif element.type == "headline_2":
                    font = headline_font_2
                else:
                    font = default_font
                # Split the text by newline. (Add text wrapping here if needed.)
                lines = text.splitlines()
                element_height = 0
                for line in lines:
                    bbox = font.getbbox(line)
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                    element_height += h + line_spacing
                total_height += element_height
            elif element.type == "image":
                pimage = await self.get_image(element.url)
                if pimage:
                    total_height += pimage.height + line_spacing

        if total_height == 0:
            logger.error("Total height for image creation is 0.")
            return None

        # Create a new blank white image that will serve as our canvas.
        combined_image = Image.new("RGB", (printer_width, total_height), "white")
        draw = ImageDraw.Draw(combined_image)

        # Second pass: render each element on the canvas.
        current_y = 0
        for element in elements:
            if element.type in ["headline_1", "headline_2", "message"]:
                text = element.text or ""
                if element.type == "headline_1":
                    font = headline_font_1
                    lines = text.splitlines()
                    for line in lines:
                        bbox = font.getbbox(line)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        # Center the headline text.
                        x = (printer_width - w) // 2
                        draw.text((x, current_y), line, fill="black", font=font)
                        current_y += h + line_spacing
                elif element.type == "headline_2":
                    font = headline_font_2
                    lines = text.splitlines()
                    for line in lines:
                        bbox = font.getbbox(line)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        x = (printer_width - w) // 2
                        draw.text((x, current_y), line, fill="black", font=font)
                        current_y += h + line_spacing
                else:  # message (left-aligned)
                    font = default_font
                    lines = text.splitlines()
                    for line in lines:
                        bbox = font.getbbox(line)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        x = 0
                        draw.text((x, current_y), line, fill="black", font=font)
                        current_y += h + line_spacing
            elif element.type == "image":
                pimage = await self.get_image(element.url)
                if pimage:
                    # Center the image horizontally.
                    x = (printer_width - pimage.width) // 2
                    combined_image.paste(pimage.convert("RGB"), (x, current_y))
                    current_y += pimage.height + line_spacing

        return combined_image
