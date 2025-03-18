from database.couchdb_client import couchdb_client
import logging

logger = logging.getLogger("uvicorn.error.overlay")

def save_overlay_data(key: str, value: str):
    """Save or update overlay data in CouchDB."""
    try:
        db = couchdb_client.get_db("overlay")

        # Check if key already exists
        existing_doc_id = next((doc for doc in db if db[doc].get("type") == "overlay" and db[doc].get("key") == key), None)

        if existing_doc_id:
            doc = db[existing_doc_id]
            doc["value"] = value
            db.save(doc)
        else:
            doc = {"_id": f"overlay_{key}", "type": "overlay", "key": key, "value": value}
            db.save(doc)

        return doc
    except Exception as e:
        logger.error(f"❌ Error saving overlay data: {e}")
        return None


def get_overlay_data(key: str):
    """Retrieve overlay data from CouchDB."""
    try:
        db = couchdb_client.get_db("overlay")

        # Find the document matching the given key
        overlay_data = next((db[doc] for doc in db if db[doc].get("type") == "overlay" and db[doc].get("key") == key), None)

        return overlay_data["value"] if overlay_data else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve overlay data: {e}")
        return None
