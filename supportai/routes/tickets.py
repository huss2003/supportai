import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..exceptions import InvalidStatusTransitionError, NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets"])


class Pagination(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int


class TicketResponse(BaseModel):
    ticket_id: str
    session_id: str
    intent: str
    priority_score: int
    priority_breakdown: dict[str, Any]
    status: str
    escalated: bool
    conversation: list[dict[str, Any]]
    created_at: str
    updated_at: str
    resolved_at: str | None


class TicketListItem(BaseModel):
    ticket_id: str
    session_id: str
    intent: str
    priority_score: int
    priority_breakdown: dict[str, Any]
    status: str
    escalated: bool
    created_at: str
    updated_at: str
    resolved_at: str | None


class TicketListResponse(BaseModel):
    tickets: list[TicketListItem]
    pagination: Pagination


class TicketUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(open|in_progress|resolved)$")


class TicketUpdateResponse(BaseModel):
    ticket_id: str
    status: str
    updated_at: str
    resolved_at: str | None


_VALID_TRANSITIONS: dict[str, list[str]] = {
    "open": ["in_progress"],
    "in_progress": ["resolved", "open"],
    "resolved": ["in_progress"],
}


@router.get("/api/tickets", response_model=TicketListResponse)
async def list_tickets(
    request: Request,
    status: str | None = Query(None, pattern=r"^(open|in_progress|resolved)$"),
    intent: str | None = Query(None, pattern=r"^(billing|technical|account|general)$"),
    priority_min: int | None = Query(None, ge=1, le=5),
    priority_max: int | None = Query(None, ge=1, le=5),
    escalated: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    export: str | None = Query(None, pattern=r"^(csv)$"),
) -> TicketListResponse | StreamingResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    if intent:
        filters["intent"] = intent
    if priority_min is not None:
        filters["priority_min"] = priority_min
    if priority_max is not None:
        filters["priority_max"] = priority_max
    if escalated is not None:
        filters["escalated"] = escalated

    try:
        result = await db.list_tickets(filters=filters, page=page, per_page=per_page)
    except Exception as e:
        logger.error("Failed to list tickets: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list tickets.")

    tickets_data = result.get("tickets", [])
    total_items = result.get("total", 0)
    total_pages = max(1, (total_items + per_page - 1) // per_page)

    if export == "csv":
        return _export_csv(tickets_data)

    tickets = [
        TicketListItem(
            ticket_id=t["ticket_id"],
            session_id=t["session_id"],
            intent=t["intent"],
            priority_score=t["priority_score"],
            priority_breakdown=t.get("priority_breakdown", {}),
            status=t["status"],
            escalated=t.get("escalated", False),
            created_at=t["created_at"],
            updated_at=t["updated_at"],
            resolved_at=t.get("resolved_at"),
        )
        for t in tickets_data
    ]

    return TicketListResponse(
        tickets=tickets,
        pagination=Pagination(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


def _export_csv(tickets: list[dict[str, Any]]) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ticket_id",
            "session_id",
            "intent",
            "priority_score",
            "status",
            "escalated",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
    )
    for t in tickets:
        writer.writerow(
            [
                t["ticket_id"],
                t["session_id"],
                t["intent"],
                t["priority_score"],
                t["status"],
                t.get("escalated", False),
                t["created_at"],
                t["updated_at"],
                t.get("resolved_at", ""),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tickets.csv"},
    )


@router.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, request: Request) -> TicketResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        ticket = await db.get_ticket(ticket_id)
    except Exception as e:
        logger.error("Failed to get ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Failed to get ticket.")

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"Ticket {ticket_id} not found.",
                "error_code": "ERR-006",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    return TicketResponse(
        ticket_id=ticket["ticket_id"],
        session_id=ticket["session_id"],
        intent=ticket["intent"],
        priority_score=ticket["priority_score"],
        priority_breakdown=ticket.get("priority_breakdown", {}),
        status=ticket["status"],
        escalated=ticket.get("escalated", False),
        conversation=ticket.get("conversation", []),
        created_at=ticket["created_at"],
        updated_at=ticket["updated_at"],
        resolved_at=ticket.get("resolved_at"),
    )


@router.patch("/api/tickets/{ticket_id}", response_model=TicketUpdateResponse)
async def update_ticket(
    ticket_id: str, body: TicketUpdateRequest, request: Request
) -> TicketUpdateResponse:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available.")

    try:
        ticket = await db.get_ticket(ticket_id)
    except Exception as e:
        logger.error("Failed to get ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Failed to get ticket.")

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"Ticket {ticket_id} not found.",
                "error_code": "ERR-006",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    current_status = ticket["status"]
    new_status = body.status

    if new_status not in _VALID_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_status_transition",
                "detail": f"Cannot transition from '{current_status}' to '{new_status}'.",
                "error_code": "ERR-002",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    resolved_at = now if new_status == "resolved" else None

    try:
        await db.update_ticket(ticket_id, status=new_status, resolved_at=resolved_at)
    except Exception as e:
        logger.error("Failed to update ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Failed to update ticket.")

    return TicketUpdateResponse(
        ticket_id=ticket_id,
        status=new_status,
        updated_at=now,
        resolved_at=resolved_at,
    )
