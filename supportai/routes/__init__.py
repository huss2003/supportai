from fastapi import APIRouter

from .health import router as health_router
from .chat import router as chat_router
from .tickets import router as tickets_router
from .faq import router as faq_router
from .admin import router as admin_router

router = APIRouter()
router.include_router(health_router)
router.include_router(chat_router)
router.include_router(tickets_router)
router.include_router(faq_router)
router.include_router(admin_router)

__all__ = ["router"]
