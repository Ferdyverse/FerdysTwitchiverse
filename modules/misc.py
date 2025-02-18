import json
import os
import config
import logging
import yaml
import datetime

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

def save_todo(todo, user):
    """Save or update Twitch tokens for a specific scope."""
    todo_file = config.TODO_FILE

    try:
        if os.path.exists(todo_file):
            try:
                with open(todo_file, "r") as f:
                    todos = json.load(f)
            except json.JSONDecodeError:
                todos = {}
        else:
            todos = {}

        todos[todo] = {
            "user": user,
            "created": str(datetime.datetime.utcnow())
        }

        with open(todo_file, "w") as f:
            json.dump(todos, f, indent=4)

        return True
    except:
        return False
