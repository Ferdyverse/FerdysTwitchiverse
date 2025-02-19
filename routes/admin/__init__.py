from fastapi import APIRouter
from .buttons import router as button_router
from .scheduled import router as scheduled_router
from .twitch import router as twitch_router
from .viewers import router as viewers_router

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(button_router)
admin_router.include_router(scheduled_router)
admin_router.include_router(twitch_router)
admin_router.include_router(viewers_router)
