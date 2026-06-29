import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("supportai.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = f"req-{uuid.uuid4()}"
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        response.headers["X-Request-Id"] = request_id

        logger.info(
            "%s %s -> %d (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
            request_id,
        )

        return response
