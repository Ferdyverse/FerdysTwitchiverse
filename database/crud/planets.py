from database.couchdb_client import couchdb_client
import datetime
import uuid
import logging

logger = logging.getLogger("uvicorn.error.planets")

def get_planets():
    """Retrieve all planets from the correct CouchDB database."""
    try:
        db = couchdb_client.get_db("planets")

        # Fetch all documents where type == "planet"
        planets = [db[doc] for doc in db if db[doc].get("type") == "planet"]

        # Sort by date (newest first)
        planets.sort(key=lambda x: x["date"], reverse=True)

        return planets
    except Exception as e:
        logger.error(f"❌ Failed to retrieve planets: {e}")
        return []

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float):
    """Save a planet record to the correct CouchDB database."""
    try:
        db = couchdb_client.get_db("planets")

        planet = {
            "_id": str(uuid.uuid4()),  # Unique identifier for CouchDB
            "type": "planet",
            "raider_name": raider_name,
            "raid_size": raid_size,
            "angle": angle,
            "distance": distance,
            "date": datetime.datetime.utcnow().isoformat()  # Store as ISO timestamp
        }

        db.save(planet)
        return planet
    except Exception as e:
        logger.error(f"❌ Error saving planet: {e}")
        return None

def clear_planets():
    """Delete all planets from the correct CouchDB database."""
    try:
        db = couchdb_client.get_db("planets")

        # Fetch all planet documents
        planet_docs = [doc for doc in db if db[doc].get("type") == "planet"]

        # Delete all found planet documents
        for doc_id in planet_docs:
            db.delete(db[doc_id])

        logger.info("✅ Cleared all planets from CouchDB.")
    except Exception as e:
        logger.error(f"❌ Failed to clear planets: {e}")
