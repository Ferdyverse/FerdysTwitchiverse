from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import Planet
import datetime

def get_planets(db: Session = Depends(get_db)):
    """Retrieve all planets."""
    try:
        return db.query(Planet).order_by(Planet.date.desc()).all()
    except Exception as e:
        print(f"❌ Failed to retrieve planets: {e}")
        return []

def save_planet(raider_name: str, raid_size: int, angle: float, distance: float, db: Session = Depends(get_db)):
    """Save a planet record."""
    try:
        planet = Planet(
            raider_name=raider_name,
            raid_size=raid_size,
            angle=angle,
            distance=distance,
            date=datetime.datetime.utcnow()
        )
        db.add(planet)
        db.commit()
        db.refresh(planet)
        return planet
    except Exception as e:
        print(f"❌ Error saving planet: {e}")
        db.rollback()
        return None

def clear_planets(db: Session = Depends(get_db)):
    """Delete all planets."""
    try:
        db.query(Planet).delete()
        db.commit()
    except Exception as e:
        print(f"❌ Failed to clear planets: {e}")
        db.rollback()
