import json
import logging
import uuid
from modules.couchdb_client import couchdb_client

logger = logging.getLogger("uvicorn.error.admin_buttons")


def get_admin_buttons():
    """Retrieve all admin buttons ordered by position from CouchDB."""
    try:
        db = couchdb_client.get_db("admin_buttons")

        buttons = [
            db[doc["id"]] for doc in db.view("_all_docs", include_docs=True)
            if db[doc["id"]].get("type") == "admin_button"
        ]
        return sorted(buttons, key=lambda x: x.get("position", 0))
    except Exception as e:
        logger.error(f"❌ Failed to retrieve admin buttons: {e}")
        return []


def add_admin_button(label: str, action: str, data: dict, prompt: bool):
    """Add a new admin button to CouchDB."""
    try:
        db = couchdb_client.get_db("admin_buttons")
        button_id = f"admin_button_{uuid.uuid4().hex}"

        button_data = {
            "_id": button_id,
            "type": "admin_button",
            "label": label,
            "action": action,
            "data": json.dumps(data) if isinstance(data, dict) else "{}",
            "prompt": prompt,
            "position": len(get_admin_buttons())  # New button at the end
        }

        db.save(button_data)
        return get_admin_buttons()  # Return updated list of buttons
    except Exception as e:
        logger.error(f"❌ Error adding admin button: {e}")
        return None


def update_admin_button(button_id: str, label: str, action: str, data: dict, prompt: bool):
    """Update an existing admin button in CouchDB."""
    try:
        db = couchdb_client.get_db("admin_buttons")
        button = db.get(button_id)

        if not button:
            return None  # Button not found

        button.update({
            "label": label,
            "action": action,
            "data": json.dumps(data) if isinstance(data, dict) else "{}",
            "prompt": prompt
        })

        db.save(button)
        return get_admin_buttons()  # Return updated list of buttons
    except Exception as e:
        logger.error(f"❌ Error updating admin button: {e}")
        return None


def remove_admin_button(button_id: str):
    """Remove an admin button from CouchDB."""
    try:
        db = couchdb_client.get_db("admin_buttons")
        if button_id in db:
            db.delete(db[button_id])
            return get_admin_buttons()  # Return updated list of buttons
        return None  # Button not found
    except Exception as e:
        logger.error(f"❌ Error removing admin button: {e}")
        return None


def reorder_admin_buttons(updated_buttons: list):
    """Update the order of admin buttons in CouchDB."""
    try:
        db = couchdb_client.get_db("admin_buttons")
        for button_data in updated_buttons:
            button = db.get(button_data["_id"])
            if button:
                button["position"] = button_data["position"]
                db.save(button)

        return True
    except Exception as e:
        logger.error(f"❌ Error reordering admin buttons: {e}")
        return False
