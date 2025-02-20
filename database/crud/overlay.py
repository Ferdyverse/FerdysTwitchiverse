from database.session import SessionLocal
from database.base import OverlayData

def save_overlay_data(key: str, value: str):
    """Save or update overlay data."""
    db = SessionLocal()
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
        return None
    finally:
        db.close()

def get_overlay_data(key: str):
    """Retrieve overlay data."""
    db = SessionLocal()
    try:
        overlay_data = db.query(OverlayData).filter_by(key=key).first()
        return overlay_data.value if overlay_data else None
    except Exception as e:
        print(f"❌ Failed to retrieve overlay data: {e}")
        return None
    finally:
        db.close()
