from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.planets import get_planets
import logging

router = APIRouter(prefix="/planets", tags=["Planets"])
logger = logging.getLogger("uvicorn.error.planets")

@router.get("/")
async def get_all_planets(db: Session = Depends(get_db)):
    """Retrieve all planets (saved raids) from the database."""
    try:
        planets = get_planets(db)

        if not planets:
            logger.info("ℹ️ No planets found in the database.")
            return []  # Return empty list instead of None

        return [
            {
                "raider_name": planet.raider_name,
                "raid_size": planet.raid_size,
                "angle": planet.angle,
                "distance": planet.distance
            }
            for planet in planets
        ]

    except Exception as e:
        logger.error(f"❌ Error retrieving planets: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving planets")
