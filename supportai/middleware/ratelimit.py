import logging
import os
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TokenBucket:
    __slots__ = ("capacity", "refill_rate", "tokens", "last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


_LIMIT_OVERRIDES: dict[str, tuple[int, float]] = {
    "/api/admin": (10, 10.0 / 60.0),
}
_SAFE = (120, 120.0 / 60.0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.default_capacity = int(os.getenv("RATE_LIMIT_DEFAULT", "60"))
        self.default_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
        self.default_refill = self.default_capacity / self.default_window
        self.buckets: dict[str, TokenBucket] = {}

    def _key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"k:{api_key}"
        host = request.client.host if request.client else "unknown"
        return f"i:{host}"

    def _limits(self, path: str, method: str) -> tuple[int, float]:
        for prefix, (cap, refill) in _LIMIT_OVERRIDES.items():
            if path.startswith(prefix):
                return (cap, refill)
        if path.startswith("/api/faq") and method in ("POST", "DELETE"):
            return (30, 30.0 / 60.0)
        if path == "/api/health":
            return _SAFE
        return (self.default_capacity, self.default_refill)

    async def dispatch(self, request: Request, call_next):
        key = self._key(request)
        capacity, refill = self._limits(request.url.path, request.method)

        if key not in self.buckets:
            self.buckets[key] = TokenBucket(capacity, refill)

        if not self.buckets[key].consume():
            logger.warning("Rate limit exceeded for %s", key)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Rate limit exceeded. Try again later.",
                    "error_code": "ERR-008",
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
