from fastapi import APIRouter, Body
from fastapi.responses import RedirectResponse
import logging
from modules.spotify import (
    spotify,
    get_auth_url,
    process_auth_code,
    handle_spotify_exception,
)

router = APIRouter(prefix="/spotify", tags=["Spotify"])
logger = logging.getLogger("uvicorn.error.spotify_router")


@router.get("/login")
def spotify_login():
    """Redirects user to Spotify login"""
    auth_url = get_auth_url()
    return RedirectResponse(auth_url)


@router.get("/auth")
def spotify_callback(code: str):
    """Handles Spotify OAuth callback"""
    access_token = process_auth_code(code)
    return (
        {"status": "Authenticated", "access_token": access_token}
        if access_token
        else {"error": "Authentication failed"}
    )


@router.get("/currently-playing")
@handle_spotify_exception
def get_current_song():
    """Fetch the currently playing song"""
    current_track = spotify.current_playback()
    if current_track and current_track.get("item"):
        return {
            "title": current_track["item"]["name"],
            "artist": ", ".join(
                artist["name"] for artist in current_track["item"]["artists"]
            ),
            "album": current_track["item"]["album"]["name"],
            "cover": current_track["item"]["album"]["images"][0]["url"],
            "volume": current_track["device"]["volume_percent"],
        }
    return {"error": "No track currently playing"}


@router.post("/play")
@handle_spotify_exception
async def play():
    """Start playback"""
    spotify.start_playback()
    return {"status": "Playing"}


@router.post("/pause")
@handle_spotify_exception
async def pause():
    """Pause playback"""
    spotify.pause_playback()
    return {"status": "Paused"}


@router.post("/next")
@handle_spotify_exception
async def next_track():
    """Skip to next track"""
    spotify.next_track()
    return {"status": "Skipped"}


@router.post("/previous")
@handle_spotify_exception
async def previous_track():
    """Go back to previous track"""
    spotify.previous_track()
    return {"status": "Rewinded"}


@router.post("/volume/{volume}")
@handle_spotify_exception
async def set_volume(volume: int):
    """Set volume (0-100)"""
    spotify.volume(volume)
    return {"status": f"Volume set to {volume}%"}
