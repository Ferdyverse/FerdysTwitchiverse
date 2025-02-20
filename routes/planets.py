from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.crud.planets import get_planets

router = APIRouter(prefix="/planets", tags=["Planets"])

@router.get("/")
async def get_all_planets(db: Session = Depends(get_db)):
    """Retrieve all planets (saved raids) from the database."""
    planets = get_planets(db)
    return [
        {
            "raider_name": planet.raider_name,
            "raid_size": planet.raid_size,
            "angle": planet.angle,
            "distance": planet.distance
        }
        for planet in planets
    ]
