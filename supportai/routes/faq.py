import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from ..exceptions import DuplicateResourceError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["FAQ"])


class FAQCreateRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    answer: str = Field(..., min_length=20, max_length=2000)
    intent_tags: list[str] = Field(..., min_length=1)

    @field_validator("intent_tags")
    @classmethod
    def validate_intent_tags(cls, v: list[str]) -> list[str]:
        valid = {"billing", "technical", "account", "general"}
        for tag in v:
            if tag not in valid:
                raise ValueError(
                    f"Invalid intent tag '{tag}'. Must be one of: {', '.join(sorted(valid))}."
                )
        return v


class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    intent_tags: list[str]
    created_at: str


class FAQListResponse(BaseModel):
    faqs: list[FAQResponse]
    pagination: dict


@router.get("/api/faq", response_model=FAQListResponse)
async def list_faqs(
    request: Request,
    intent: str | None = Query(None, pattern=r"^(billing|technical|account|general)$"),
    search: str | None = Query(None, min_length=2),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> FAQListResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    filters: dict = {}
    if intent:
        filters["intent"] = intent
    if search:
        filters["search"] = search

    try:
        result = await db.list_faqs(filters=filters, page=page, per_page=per_page)
    except Exception as e:
        logger.error("Failed to list FAQs: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list FAQs.")

    faq_items = result.get("faqs", [])
    total = result.get("total", 0)

    faqs = [
        FAQResponse(
            id=f["id"],
            question=f["question"],
            answer=f["answer"],
            intent_tags=f.get("intent_tags", []),
            created_at=f["created_at"],
        )
        for f in faq_items
    ]

    return FAQListResponse(
        faqs=faqs,
        pagination={
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    )


@router.post("/api/faq", response_model=FAQResponse, status_code=201)
async def create_faq(body: FAQCreateRequest, request: Request) -> FAQResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        existing = await db.find_faq_by_question(body.question)
    except Exception as e:
        logger.error("Failed to check duplicate FAQ: %s", e)
        raise HTTPException(status_code=500, detail="Failed to check FAQ uniqueness.")

    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_resource",
                "detail": f"FAQ with question '{body.question[:50]}...' already exists.",
                "error_code": "ERR-007",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    try:
        faq = await db.create_faq(
            question=body.question,
            answer=body.answer,
            intent_tags=body.intent_tags,
        )
    except Exception as e:
        logger.error("Failed to create FAQ: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create FAQ.")

    return FAQResponse(
        id=faq["id"],
        question=faq["question"],
        answer=faq["answer"],
        intent_tags=faq.get("intent_tags", []),
        created_at=faq["created_at"],
    )


@router.delete("/api/faq/{faq_id}", status_code=204)
async def delete_faq(faq_id: int, request: Request) -> None:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        faq = await db.get_faq(faq_id)
    except Exception as e:
        logger.error("Failed to get FAQ %d: %s", faq_id, e)
        raise HTTPException(status_code=500, detail="Failed to get FAQ.")

    if faq is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"FAQ with id {faq_id} not found.",
                "error_code": "ERR-006",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    try:
        await db.delete_faq(faq_id)
    except Exception as e:
        logger.error("Failed to delete FAQ %d: %s", faq_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete FAQ.")
