import logging
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    models_loaded: bool
    db_connected: bool
    sessions_active: int
    tickets_open: int
    memory_usage_mb: float


@router.get("/api/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    uptime = time.time() - request.app.state.startup_time

    pipeline = getattr(request.app.state, "pipeline", None)
    db = getattr(request.app.state, "db", None)

    db_connected = False
    if db is not None:
        try:
            db_connected = db.is_connected()
        except Exception:
            db_connected = False

    models_loaded = pipeline is not None

    status = "healthy"
    if not models_loaded:
        status = "degraded"
    if not db_connected:
        status = "degraded"

    try:
        import psutil as _psutil

        memory = _psutil.Process().memory_info().rss / 1024 / 1024
    except ImportError:
        memory = 0.0

    try:
        from ..services.session import SessionManager

        sessions_active = SessionManager.active_count()
    except Exception:
        sessions_active = 0

    tickets_open = 0
    if db is not None:
        try:
            tickets_open = await db.count_tickets_by_status("open")
        except Exception:
            tickets_open = 0

    return HealthResponse(
        status=status,
        version="2.0.0",
        uptime_seconds=round(uptime, 1),
        models_loaded=models_loaded,
        db_connected=db_connected,
        sessions_active=sessions_active,
        tickets_open=tickets_open,
        memory_usage_mb=round(memory, 1),
    )
