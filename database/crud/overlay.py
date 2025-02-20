from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import OverlayData

def save_overlay_data(key: str, value: str, db: Session = Depends(get_db)):
    """Save or update overlay data."""
    try:
        overlay_data = db.query(OverlayData).filter_by(key=key).first()
        if overlay_data:
            overlay_data.value = value
        else:
            overlay_data = OverlayData(key=key, value=value)
            db.add(overlay_data)
        db.commit()
        return overlay_data
    except Exception as e:
        print(f"❌ Error saving overlay data: {e}")
        db.rollback()
        return None

def get_overlay_data(key: str, db: Session = Depends(get_db)):
    """Retrieve overlay data."""
    try:
        overlay_data = db.query(OverlayData).filter_by(key=key).first()
        return overlay_data.value if overlay_data else None
    except Exception as e:
        print(f"❌ Failed to retrieve overlay data: {e}")
        return None
