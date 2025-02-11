import json
import os
import config
import logging

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

    tokens[scope] = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

    # ✅ Save updated tokens back to file
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
