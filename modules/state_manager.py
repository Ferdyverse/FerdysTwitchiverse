import json
import os
import logging
import config

logger = logging.getLogger("uvicorn.error.state_manager")

CONDITIONS = {}

def load_states():
    """ Load conditions from a file into memory. """
    global CONDITIONS
    if os.path.exists(config.STATE_FILE):
        try:
            with open(config.STATE_FILE, "r") as file:
                CONDITIONS = json.load(file)
            logger.info("✅ Loaded conditions from state.json")
        except json.JSONDecodeError:
            logger.warning("⚠️ Corrupt state.json file. Resetting states.")
            CONDITIONS = {}
    else:
        CONDITIONS = {}

def save_states():
    """ Save conditions to a file. """
    try:
        with open(config.STATE_FILE, "w") as file:
            json.dump(CONDITIONS, file, indent=2)
        logger.info("✅ Conditions saved to state.json")
    except Exception as e:
        logger.error(f"❌ Failed to save state.json: {e}")

def set_condition(name: str, value: bool):
    """ Set a condition in memory and persist it. """
    CONDITIONS[name] = value
    save_states()
    logger.info(f"🔄 Condition '{name}' set to {value}")

def check_condition(name: str) -> bool:
    """ Check if a condition exists and is True. """
    return CONDITIONS.get(name, False)

# ✅ Load states on startup
load_states()
