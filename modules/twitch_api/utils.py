import logging

logger = logging.getLogger("uvicorn.error.twitch_api.utils")


def format_time(time_str):
    """Format a timestamp into a readable time format."""
    return time_str.strftime("%H:%M:%S")
