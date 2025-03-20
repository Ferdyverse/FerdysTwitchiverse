import json
import os
import config
import logging
import yaml
import html

logger = logging.getLogger("uvicorn.error.misc")


def save_tokens(scope, access_token, refresh_token):
    """Save or update Twitch tokens for a specific scope."""
    token_file = config.TOKEN_FILE

    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                tokens = json.load(f)
        except json.JSONDecodeError:
            tokens = {}
    else:
        tokens = {}

    tokens[scope] = {"access_token": access_token, "refresh_token": refresh_token}

    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=4)

    logger.info(f"✅ Tokens saved for scope: {scope}")  # Debugging output


def load_tokens(scope):
    """Load Twitch tokens from a file."""
    try:
        with open(config.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
            logger.info("Tokens loaded!")
            if scope in tokens:
                return tokens[scope]
            else:
                return None
    except FileNotFoundError:
        return None


def load_sequences():
    """Load action sequences from YAML file."""
    if not os.path.exists(config.SEQUENCES_FILE):
        return {}  # Return empty if no YAML file exists

    with open(config.SEQUENCES_FILE, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("sequences", {})


def replace_emotes(message: str, emotes: dict) -> str:
    """Replace emote text in a message with Twitch emote images inline."""
    if not emotes:
        return html.escape(message)  # Escape HTML to prevent XSS

    emote_replacements = []

    # Iterate over each emote ID and its positions
    for emote_id, positions in emotes.items():
        for pos in positions:
            start = int(pos["start_position"])
            end = int(pos["end_position"])
            emote_img = f'<img src="https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0" class="twitch-emote">'
            emote_replacements.append((start, end, emote_img))

    # Sort emote positions from last to first (to avoid index shift)
    emote_replacements.sort(reverse=True, key=lambda x: x[0])

    # Escape message text first (so HTML tags in normal text are safe)
    message = html.escape(message)

    # Replace text with image HTML (from back to front)
    for start, end, img in emote_replacements:
        message = message[:start] + img + message[end + 1 :]

    return message
