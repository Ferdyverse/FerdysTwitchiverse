# config.py
from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

def getenv_bool(var_name: str, default: bool = False) -> bool:
    """Retrieve an environment variable as a boolean."""
    return os.getenv(var_name, str(default)).strip().lower() in ("true", "1", "yes", "on")

def getenv_int(var_name: str, default: int = 0) -> int:
    """Retrieve an environment variable as an integer."""
    try:
        return int(os.getenv(var_name, default))
    except ValueError:
        return default

DISABLE_HEAT_API = getenv_bool("DISABLE_HEAT_API")
DISABLE_FIREBOT = getenv_bool("DISABLE_FIREBOT")
DISABLE_PRINTER = getenv_bool("DISABLE_PRINTER")
DISABLE_TWITCH = getenv_bool("DISABLE_TWITCH")
DISABLE_OBS = getenv_bool("DISABLE_OBS")
USE_MOCK_API = getenv_bool("ENABLE_MOCK_API")

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

if USE_MOCK_API:
    print("⚠️ Using Twitch Mock API")
    TWITCH_CLIENT_ID = "2b9b72c93c0154e624b6abdee104bc"
    TWITCH_CLIENT_SECRET = "b66a128609232b7153265668f5c0a5"
    TWITCH_CHANNEL = "mock-channel"
    TWITCH_CHANNEL_ID = "79606119"
    TWITCH_API_BASE_URL = "http://localhost:8080/"
else:
    print("✅ Using Live Twitch API")
    TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
    TWITCH_CHANNEL = "Ferdyverse"
    TWITCH_CHANNEL_ID = 136134545 # Ferdyverse
    TWITCH_API_BASE_URL = "https://api.twitch.tv/helix"

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    raise RuntimeError("🚨 Missing Twitch credentials! Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET in .env")

# OBS
OBS_WS_HOST = "localhost"
OBS_WS_PORT = 4455
OBS_WS_PASSWORD = os.getenv("OBS_WS_PASSWORD")

# FIREBOT
FIREBOT_API_URL = "http://localhost:7472/api/v1"

# Additional settings
TOKEN_FILE = "twitch_tokens.json"
SEQUENCES_FILE = "storage/sequences.yaml"
STATE_FILE = "storage/state.json"
COMMAND_RESPONSES_FILE = "storage/command_responses.json"
