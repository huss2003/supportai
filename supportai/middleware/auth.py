import logging
import os
import re
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

EXEMPT_PATHS = [
    re.compile(r"^/api/health$"),
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        for pattern in EXEMPT_PATHS:
            if pattern.match(request.url.path):
                return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        valid_keys = os.getenv("SUPPORTAI_API_KEYS", "").split(",")
        valid_keys = [k.strip() for k in valid_keys if k.strip()]

        if not api_key:
            logger.warning("Missing API key for %s", request.url.path)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "detail": "Missing API key.",
                    "error_code": "ERR-004",
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
            )

        if api_key not in valid_keys:
            logger.warning("Invalid API key for %s", request.url.path)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "detail": "Invalid API key.",
                    "error_code": "ERR-005",
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
            )

        return await call_next(request)
