from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.base import Planet
import datetime

async def get_planets(db: AsyncSession = Depends(get_db)):
    """Retrieve all planets asynchronously."""
    try:
        result = await db.execute(select(Planet).order_by(Planet.date.desc()))
        return result.scalars().all()
    except Exception as e:
        print(f"❌ Failed to retrieve planets: {e}")
        return []

async def save_planet(raider_name: str, raid_size: int, angle: float, distance: float, db: AsyncSession = Depends(get_db)):
    """Save a planet record asynchronously."""
    try:
        planet = Planet(
            raider_name=raider_name,
            raid_size=raid_size,
            angle=angle,
            distance=distance,
            date=datetime.datetime.utcnow()
        )
        db.add(planet)
        await db.commit()
        await db.refresh(planet)
        return planet
    except Exception as e:
        print(f"❌ Error saving planet: {e}")
        await db.rollback()
        return None

async def clear_planets(db: AsyncSession = Depends(get_db)):
    """Delete all planets asynchronously."""
    try:
        await db.execute(select(Planet).delete())  # Delete all records
        await db.commit()
    except Exception as e:
        print(f"❌ Failed to clear planets: {e}")
        await db.rollback()
