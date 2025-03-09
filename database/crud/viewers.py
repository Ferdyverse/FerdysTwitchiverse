from fastapi import Depends
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.base import Viewer, ViewerStats
import logging

logger = logging.getLogger("uvicorn.error.viewers")

async def get_viewer(twitch_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a viewer by Twitch ID asynchronously."""
    try:
        result = await db.execute(select(Viewer).filter(Viewer.twitch_id == twitch_id))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"❌ Failed to retrieve viewer: {e}")
        return None

async def save_viewer(
    twitch_id: int,
    login: str = "",
    display_name: str = "",
    account_type: str = "",
    broadcaster_type: str = "",
    profile_image_url: str = "",
    account_age: str = "",
    follower_date: datetime.datetime = None,
    subscriber_date: datetime.datetime = None,
    color: str = "",
    badges: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Save or update viewer data asynchronously."""
    try:
        result = await db.execute(select(Viewer).filter(Viewer.twitch_id == twitch_id))
        viewer = result.scalars().first()

        if viewer:
            viewer.display_name = display_name or viewer.display_name
            viewer.account_type = account_type or viewer.account_type
            viewer.broadcaster_type = broadcaster_type or viewer.broadcaster_type
            viewer.profile_image_url = profile_image_url or viewer.profile_image_url
            viewer.account_age = account_age or viewer.account_age
            viewer.follower_date = follower_date if follower_date else viewer.follower_date
            viewer.subscriber_date = subscriber_date if subscriber_date else viewer.subscriber_date
            viewer.color = color or viewer.color
            viewer.badges = badges or viewer.badges
        else:
            viewer = Viewer(
                twitch_id=twitch_id,
                login=login,
                display_name=display_name,
                account_type=account_type,
                broadcaster_type=broadcaster_type,
                profile_image_url=profile_image_url,
                account_age=account_age,
                follower_date=follower_date,
                subscriber_date=subscriber_date,
                color=color,
                badges=badges
            )
            db.add(viewer)

        await db.commit()
        await db.refresh(viewer)
        return viewer
    except Exception as e:
        logger.error(f"❌ Failed to save viewer: {e}")
        await db.rollback()
        return None

async def get_viewer_stats(twitch_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific viewer's data along with chat stats asynchronously."""
    try:
        result = await db.execute(select(Viewer).filter(Viewer.twitch_id == twitch_id))
        viewer = result.scalars().first()

        if not viewer:
            return None

        stats_result = await db.execute(select(ViewerStats).filter(ViewerStats.twitch_id == twitch_id))
        stream_stats = stats_result.scalars().all()

        return {
            "twitch_id": viewer.twitch_id,
            "login": viewer.login,
            "display_name": viewer.display_name,
            "total_chat_messages": viewer.total_chat_messages,
            "total_used_emotes": viewer.total_used_emotes,
            "total_replies": viewer.total_replies,
            "per_stream_stats": [
                {
                    "stream_id": stat.stream_id,
                    "chat_messages": stat.chat_messages,
                    "used_emotes": stat.used_emotes,
                    "replies": stat.replies,
                    "last_message_time": stat.last_message_time
                }
                for stat in stream_stats
            ]
        }
    except Exception as e:
        logger.error(f"❌ Failed to retrieve viewer stats: {e}")
        return None

async def update_viewer_stats(twitch_id: int, stream_id: str, emotes_used: int, is_reply: bool, db: AsyncSession = Depends(get_db)):
    """Update viewer stats asynchronously."""
    try:
        result = await db.execute(select(Viewer).filter(Viewer.twitch_id == twitch_id))
        viewer = result.scalars().first()

        if viewer:
            viewer.total_chat_messages += 1
            viewer.total_used_emotes += emotes_used
            viewer.total_replies += 1 if is_reply else 0
            await db.commit()

        stats_result = await db.execute(select(ViewerStats).filter(ViewerStats.twitch_id == twitch_id, ViewerStats.stream_id == stream_id))
        stats = stats_result.scalars().first()

        if stats:
            stats.chat_messages += 1
            stats.used_emotes += emotes_used
            stats.replies += 1 if is_reply else 0
            stats.last_message_time = datetime.datetime.utcnow()
        else:
            stats = ViewerStats(
                twitch_id=twitch_id,
                stream_id=stream_id,
                chat_messages=1,
                used_emotes=emotes_used,
                replies=1 if is_reply else 0
            )
            db.add(stats)

        await db.commit()
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to update viewer stats: {e}")
        await db.rollback()
        return None
