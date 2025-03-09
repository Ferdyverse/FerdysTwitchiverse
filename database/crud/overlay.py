from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.base import OverlayData

async def save_overlay_data(key: str, value: str, db: AsyncSession = Depends(get_db)):
    """Save or update overlay data asynchronously."""
    try:
        result = await db.execute(select(OverlayData).filter_by(key=key))
        overlay_data = result.scalars().first()

        if overlay_data:
            overlay_data.value = value
        else:
            overlay_data = OverlayData(key=key, value=value)
            db.add(overlay_data)

        await db.commit()
        return overlay_data
    except Exception as e:
        print(f"❌ Error saving overlay data: {e}")
        await db.rollback()
        return None

async def get_overlay_data(key: str, db: AsyncSession = Depends(get_db)):
    """Retrieve overlay data asynchronously."""
    try:
        result = await db.execute(select(OverlayData).filter_by(key=key))
        overlay_data = result.scalars().first()
        return overlay_data.value if overlay_data else None
    except Exception as e:
        print(f"❌ Failed to retrieve overlay data: {e}")
        return None
