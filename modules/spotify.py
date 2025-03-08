from fastapi import HTTPException
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import functools
import inspect
import logging
import config

logger = logging.getLogger("uvicorn.error.spotify")


# Initialize Spotipy with OAuth
auth_manager = SpotifyOAuth(
    client_id=config.SPOTIFY_CLIENT_ID,
    client_secret=config.SPOTIFY_CLIENT_SECRET,
    redirect_uri=config.SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing user-read-playback-state user-modify-playback-state"
)

spotify = spotipy.Spotify(auth_manager=auth_manager)

def get_auth_url():
    """Returns Spotify login URL"""
    return auth_manager.get_authorize_url()

def process_auth_code(code):
    """Processes the Spotify OAuth callback"""
    token_info = auth_manager.get_access_token(code)
    return token_info["access_token"] if token_info else None

def handle_spotify_exception(func):
    """Decorator to handle Spotipy exceptions properly"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)  # Await if function is async
            return func(*args, **kwargs)  # Call normally if function is sync
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API Error: {e}")
            error_message = e.msg

            if "NO_ACTIVE_DEVICE" in error_message:
                raise HTTPException(status_code=400, detail="No active Spotify device found.")
            if e.http_status == 403:
                raise HTTPException(status_code=403, detail="Spotify command forbidden (e.g., playing restricted content).")
            if e.http_status == 401:
                raise HTTPException(status_code=401, detail="Unauthorized. Please log in again.")

            raise HTTPException(status_code=e.http_status, detail=error_message)
    return async_wrapper
