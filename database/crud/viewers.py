from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import Viewer

def get_viewer(twitch_id: int, db: Session = Depends(get_db)):
    """Retrieve a viewer by Twitch ID."""
    try:
        return db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
    except Exception as e:
        print(f"❌ Failed to retrieve viewer: {e}")
        return None

def save_viewer(twitch_id: int, login: str, display_name: str, profile_image_url: str, db: Session = Depends(get_db)):
    """Save or update a viewer."""
    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
        if viewer:
            viewer.login = login
            viewer.display_name = display_name
            viewer.profile_image_url = profile_image_url
        else:
            viewer = Viewer(
                twitch_id=twitch_id,
                login=login,
                display_name=display_name,
                profile_image_url=profile_image_url
            )
            db.add(viewer)
        db.commit()
        db.refresh(viewer)
        return viewer
    except Exception as e:
        print(f"❌ Error saving viewer: {e}")
        db.rollback()
        return None
