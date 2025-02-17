# config.py
from dotenv import load_dotenv
import os

load_dotenv()

# App configuration
APP_HOST = "0.0.0.0"
APP_PORT = 8000
APP_LOG_LEVEL = "info"
APP_LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Printer configuration
PRINTER_VENDOR_ID = 0x0aa7  # WINCOR NIXDORF
PRINTER_PRODUCT_ID = 0x0304  # TH230
PRINTER_IN_EP = 0x81
PRINTER_OUT_EP = 0x02
PRINTER_PROFILE = "TH230"

# Twitch Channel STUFF
TWITCH_CHANNEL = "Ferdyverse"
TWITCH_CHANNEL_ID = 136134545 # Ferdyverse
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TOKEN_FILE = "twitch_tokens.json"

# OBS
OBS_WS_HOST = "localhost"
OBS_WS_PORT = 4455
OBS_WS_PASSWORD = os.getenv("OBS_WS_PASSWORD")

# FIREBOT
FIREBOT_API_URL = "http://localhost:7472/api/v1"

# Additional settings
SEQUENCES_FILE = "sequences.yaml"
STATE_FILE = "state.json"
TODO_FILE = "todo.json"
