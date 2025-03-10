from fastapi import APIRouter
from database.crud.planets import get_planets

router = APIRouter(prefix="/planets", tags=["Planets"])

@router.get("/")
async def get_all_planets():
    """Retrieve all planets (saved raids) from CouchDB."""
    planets = get_planets()

    return [
        {
            "raider_name": planet.get("raider_name"),
            "raid_size": planet.get("raid_size"),
            "angle": planet.get("angle"),
            "distance": planet.get("distance")
        }
        for planet in planets
    ]
