import json
import config

def save_tokens(scope, access_token, refresh_token):
    """Save Twitch tokens to a file."""
    with open(config.TOKEN_FILE, "w") as f:
        json.dump({scope: { "access_token": access_token, "refresh_token": refresh_token } }, f)


def load_tokens(scope):
    """Load Twitch tokens from a file."""
    try:
        with open(config.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
            return tokens.scope
    except FileNotFoundError:
        return None
