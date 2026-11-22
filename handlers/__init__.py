from aiogram import Router

from .admin import router as admin_router
from .moderation import router as moderation_router
from .filters import router as filters_router
from .captcha import router as captcha_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(admin_router)
    root.include_router(moderation_router)
    root.include_router(captcha_router)
    root.include_router(filters_router)
    return root
