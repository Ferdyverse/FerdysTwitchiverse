from fastapi import APIRouter
from .buttons import router as button_router
from .events import router as event_router
from .scheduled import router as scheduled_router
from .twitch import router as twitch_router
from .viewers import router as viewers_router
from .stream import router as stream_router

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(button_router)
admin_router.include_router(event_router)
admin_router.include_router(scheduled_router)
admin_router.include_router(twitch_router)
admin_router.include_router(viewers_router)
admin_router.include_router(stream_router)
