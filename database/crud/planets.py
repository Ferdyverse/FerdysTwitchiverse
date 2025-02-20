from database.session import SessionLocal
from database.base import Planet
import datetime

def get_planets():
    """Retrieve all planets."""
    db = SessionLocal()
    try:
        return db.query(Planet).order_by(Planet.date.desc()).all()
    except Exception as e:
        print(f"❌ Failed to retrieve planets: {e}")
        return []
    finally:
        db.close()

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float):
    """Save a planet record."""
    db = SessionLocal()
    try:
        planet = Planet(raider_name=raider_name, raid_size=raid_size, angle=angle, distance=distance,
                        date=datetime.datetime.utcnow())
        db.add(planet)
        db.commit()
        db.refresh(planet)
        return planet
    except Exception as e:
        print(f"❌ Error saving planet: {e}")
        return None
    finally:
        db.close()

def clear_planets():
    """Delete all planets."""
    db = SessionLocal()
    try:
        db.query(Planet).delete()
        db.commit()
    except Exception as e:
        print(f"❌ Failed to clear planets: {e}")
    finally:
        db.close()
