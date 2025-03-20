# config.py
from dotenv import load_dotenv
import os
import pytz

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)


def getenv_bool(var_name: str, default: bool = False) -> bool:
    """Retrieve an environment variable as a boolean."""
    return os.getenv(var_name, str(default)).strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def getenv_int(var_name: str, default: int = 0) -> int:
    """Retrieve an environment variable as an integer."""
    try:
        return int(os.getenv(var_name, default))
    except ValueError:
        return default


DISABLE_HEAT_API = getenv_bool("DISABLE_HEAT_API")
DISABLE_PRINTER = getenv_bool("DISABLE_PRINTER")
DISABLE_TWITCH = getenv_bool("DISABLE_TWITCH")
DISABLE_OBS = getenv_bool("DISABLE_OBS")
DISABLE_SPOTIFY = getenv_bool("DISABLE_SPOTIFY")
USE_MOCK_API = getenv_bool("ENABLE_MOCK_API")

# App configuration
APP_HOST = "0.0.0.0"
APP_PORT = 8000
APP_LOG_LEVEL = "info"
APP_LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
APP_DOMAIN = "http://localhost:8000"

# Printer configuration
PRINTER_VENDOR_ID = 0x0AA7  # WINCOR NIXDORF
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
    TWITCH_CHANNEL_ID = 136134545  # Ferdyverse
    TWITCH_API_BASE_URL = "https://api.twitch.tv/helix"
    TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    raise RuntimeError(
        "🚨 Missing Twitch credentials! Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET in .env"
    )

# Database
COUCHDB_USER = os.getenv("COUCHDB_USER", "admin")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD", "password")
COUCHDB_HOST = "localhost"
COUCHDB_PORT = "5984"
COUCHDB_URL = f"http://{COUCHDB_USER}:{COUCHDB_PASSWORD}@{COUCHDB_HOST}:{COUCHDB_PORT}"

# OBS
OBS_WS_HOST = "localhost"
OBS_WS_PORT = 4455
OBS_WS_PASSWORD = os.getenv("OBS_WS_PASSWORD")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TTS_AUDIO_PATH = "static/sounds/tts/"  # Directory for storing TTS files

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://localhost:8000/spotify/auth"

# Additional settings
TOKEN_FILE = "storage/twitch_tokens.json"
SEQUENCES_FILE = "storage/sequences.yaml"
STATE_FILE = "storage/state.json"
COMMAND_RESPONSES_FILE = "storage/command_responses.json"
LOCAL_TIMEZONE = pytz.timezone("Europe/Berlin")
