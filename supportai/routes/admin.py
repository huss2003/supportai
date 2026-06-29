import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


class TrendIndicator(BaseModel):
    value: float
    direction: str
    percentage_change: float


class IntentBreakdownItem(BaseModel):
    intent: str
    count: int
    percentage: float


class DailyVolumeItem(BaseModel):
    date: str
    billing: int
    technical: int
    account: int
    general: int
    total: int


class ResolutionRateItem(BaseModel):
    date: str
    resolved: int
    total: int
    rate: float


class MetricsResponse(BaseModel):
    total_conversations: int
    auto_resolved: int
    escalated: int
    resolution_rate: float
    avg_handling_time_seconds: float
    csat_score: float | None
    trends: dict[str, TrendIndicator]
    intent_breakdown: list[IntentBreakdownItem]
    daily_volume: list[DailyVolumeItem]
    resolution_rate_over_time: list[ResolutionRateItem]
    top_keywords: list[dict[str, Any]]


@router.get("/api/admin/metrics", response_model=MetricsResponse)
async def get_metrics(
    request: Request,
    days: int = Query(7, ge=1, le=90),
) -> MetricsResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        metrics = await db.compute_metrics(days=days)
    except Exception as e:
        logger.error("Failed to compute metrics: %s", e)
        raise HTTPException(status_code=500, detail="Failed to compute metrics.")

    total = metrics.get("total_conversations", 0)
    auto_resolved = metrics.get("auto_resolved", 0)
    escalated_count = metrics.get("escalated", 0)

    resolution_rate = round((auto_resolved / total * 100) if total > 0 else 0.0, 1)

    return MetricsResponse(
        total_conversations=total,
        auto_resolved=auto_resolved,
        escalated=escalated_count,
        resolution_rate=resolution_rate,
        avg_handling_time_seconds=round(
            metrics.get("avg_handling_time_seconds", 0.0), 1
        ),
        csat_score=round(metrics["csat_score"], 2)
        if metrics.get("csat_score") is not None
        else None,
        trends={k: TrendIndicator(**v) for k, v in metrics.get("trends", {}).items()},
        intent_breakdown=[
            IntentBreakdownItem(**item) for item in metrics.get("intent_breakdown", [])
        ],
        daily_volume=[
            DailyVolumeItem(**item) for item in metrics.get("daily_volume", [])
        ],
        resolution_rate_over_time=[
            ResolutionRateItem(**item)
            for item in metrics.get("resolution_rate_over_time", [])
        ],
        top_keywords=metrics.get("top_keywords", []),
    )
