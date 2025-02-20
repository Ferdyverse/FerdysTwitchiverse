from database.session import SessionLocal
from database.base import Viewer

def get_viewer(twitch_id: int):
    """Retrieve a viewer by Twitch ID."""
    db = SessionLocal()
    try:
        return db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
    finally:
        db.close()

def save_viewer(twitch_id: int, login: str, display_name: str, profile_image_url: str):
    """Save or update a viewer."""
    db = SessionLocal()
    try:
        viewer = db.query(Viewer).filter(Viewer.twitch_id == twitch_id).first()
        if viewer:
            viewer.login = login
            viewer.display_name = display_name
            viewer.profile_image_url = profile_image_url
        else:
            viewer = Viewer(twitch_id=twitch_id, login=login, display_name=display_name, profile_image_url=profile_image_url)
            db.add(viewer)
        db.commit()
        db.refresh(viewer)
        return viewer
    except Exception as e:
        print(f"❌ Error saving viewer: {e}")
        return None
    finally:
        db.close()
