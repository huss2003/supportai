from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class SupportAIError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        http_status: int = 500,
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.details = details or {}


class ValidationError(SupportAIError):
    def __init__(
        self,
        message: str = "Invalid request.",
        error_code: str = "ERR-001",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 400, details)


class InvalidStatusTransitionError(SupportAIError):
    def __init__(
        self,
        message: str = "Invalid status transition.",
        error_code: str = "ERR-002",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 400, details)


class MessageTooLongError(SupportAIError):
    def __init__(
        self,
        message: str = "Message exceeds character limit.",
        error_code: str = "ERR-003",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 400, details)


class AuthenticationError(SupportAIError):
    def __init__(
        self, message: str, error_code: str = "ERR-004", details: dict | None = None
    ) -> None:
        super().__init__(message, error_code, 401, details)


class NotFoundError(SupportAIError):
    def __init__(
        self,
        message: str = "Resource not found.",
        error_code: str = "ERR-006",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 404, details)


class DuplicateResourceError(SupportAIError):
    def __init__(
        self,
        message: str = "Resource already exists.",
        error_code: str = "ERR-007",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 409, details)


class RateLimitError(SupportAIError):
    def __init__(
        self,
        message: str = "Rate limit exceeded.",
        error_code: str = "ERR-008",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 429, details)


class InternalError(SupportAIError):
    def __init__(
        self,
        message: str = "Internal server error.",
        error_code: str = "ERR-009",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 500, details)


class ServiceUnavailableError(SupportAIError):
    def __init__(
        self,
        message: str = "Service unavailable.",
        error_code: str = "ERR-010",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, error_code, 503, details)


def _error_response(request: Request, exc: SupportAIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": exc.__class__.__name__,
            "detail": exc.message,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        headers={"X-Request-Id": getattr(request.state, "request_id", "")},
    )


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(SupportAIError)
    async def supportai_error_handler(
        request: Request, exc: SupportAIError
    ) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An unexpected error occurred.",
                "error_code": "ERR-009",
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            },
            headers={"X-Request-Id": getattr(request.state, "request_id", "")},
        )
