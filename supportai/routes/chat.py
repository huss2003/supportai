import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from ..exceptions import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)
    metadata: dict[str, Any] = {}

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        import re

        v = re.sub(r"<[^>]*>", "", v)
        v = " ".join(v.split())
        return v.strip()


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    intent_confidence: float
    faq_match: dict[str, Any] | None
    sentiment: dict[str, Any]
    escalation_offered: bool
    ticket_created: dict[str, Any] | None
    timing_ms: int
    response_method: str


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    start = time.time()

    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "detail": "Chat pipeline not initialized.",
                "error_code": "ERR-010",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    if len(body.message) > 2000:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "detail": "Message exceeds 2000 character limit.",
                "error_code": "ERR-003",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    try:
        result = await pipeline.process(
            session_id=body.session_id,
            message=body.message,
            metadata=body.metadata,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    elapsed = int((time.time() - start) * 1000)

    return ChatResponse(
        session_id=result.get("session_id", body.session_id or str(uuid.uuid4())),
        reply=result.get("reply", ""),
        intent=result.get("intent", "general"),
        intent_confidence=result.get("intent_confidence", 0.0),
        faq_match=result.get("faq_match"),
        sentiment=result.get(
            "sentiment", {"label": "neutral", "score": 0.0, "normalized_score": 0.0}
        ),
        escalation_offered=result.get("escalation_offered", False),
        ticket_created=result.get("ticket_created"),
        timing_ms=elapsed,
        response_method=result.get("response_method", "template_fallback"),
    )
