import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session as SASession, sessionmaker

from supportai.db.models import Base, FAQEntry, Feedback, Message, Session, Ticket

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///supportai.db",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


async def get_db() -> AsyncGenerator[SASession, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Generator[SASession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_stats() -> dict:
    db = SessionLocal()
    try:
        session_count = db.query(Session).count()
        active_sessions = db.query(Session).filter(Session.status == "active").count()
        message_count = db.query(Message).count()
        ticket_count = db.query(Ticket).count()
        open_tickets = (
            db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress"])).count()
        )
        faq_count = db.query(FAQEntry).count()

        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        messages_24h = db.query(Message).filter(Message.created_at >= last_24h).count()

        avg_rating = db.query(Feedback.rating).all()
        csat = (
            round(sum(r[0] for r in avg_rating) / len(avg_rating), 2)
            if avg_rating
            else None
        )

        return {
            "sessions_total": session_count,
            "sessions_active": active_sessions,
            "messages_total": message_count,
            "messages_24h": messages_24h,
            "tickets_total": ticket_count,
            "tickets_open": open_tickets,
            "faq_entries": faq_count,
            "csat_avg": csat,
        }
    finally:
        db.close()


import json as _json
import uuid as _uuid


class Database:
    """Async-friendly wrapper around SQLAlchemy for the SupportAI app state."""

    async def connect(self) -> None:
        init_db()

    async def disconnect(self) -> None:
        engine.dispose()

    def is_connected(self) -> bool:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def _session_sync(self):
        return SessionLocal()

    # -- tickets -----------------------------------------------------------

    async def list_tickets(
        self, filters: dict | None = None, page: int = 1, per_page: int = 50
    ) -> dict:
        filters = filters or {}

        def _sync():
            db = self._session_sync()
            try:
                q = db.query(Ticket)
                if filters.get("status"):
                    q = q.filter(Ticket.status == filters["status"])
                if filters.get("intent"):
                    q = q.filter(Ticket.intent == filters["intent"])
                if filters.get("escalated") is not None:
                    q = q.filter(Ticket.escalated == (1 if filters["escalated"] else 0))
                total = q.count()
                q = q.order_by(Ticket.created_at.desc())
                q = q.offset((page - 1) * per_page).limit(per_page)
                tickets = []
                for t in q.all():
                    tickets.append(
                        {
                            "ticket_id": t.ticket_id,
                            "session_id": t.session_id,
                            "intent": t.intent,
                            "priority_score": t.priority_score,
                            "priority_breakdown": _json.loads(t.priority_breakdown)
                            if t.priority_breakdown
                            else {},
                            "status": t.status,
                            "escalated": bool(t.escalated),
                            "created_at": t.created_at.isoformat()
                            if t.created_at
                            else "",
                            "updated_at": t.updated_at.isoformat()
                            if t.updated_at
                            else "",
                            "resolved_at": t.resolved_at.isoformat()
                            if t.resolved_at
                            else None,
                            "conversation": [],
                        }
                    )
                return {"tickets": tickets, "total": total}
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def get_ticket(self, ticket_id: str) -> dict | None:
        def _sync():
            db = self._session_sync()
            try:
                t = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
                if t is None:
                    return None
                msgs = (
                    db.query(Message)
                    .filter(Message.session_id == t.session_id)
                    .order_by(Message.created_at)
                    .all()
                )
                return {
                    "ticket_id": t.ticket_id,
                    "session_id": t.session_id,
                    "intent": t.intent,
                    "priority_score": t.priority_score,
                    "priority_breakdown": _json.loads(t.priority_breakdown)
                    if t.priority_breakdown
                    else {},
                    "status": t.status,
                    "escalated": bool(t.escalated),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                    "updated_at": t.updated_at.isoformat() if t.updated_at else "",
                    "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                    "conversation": [
                        {
                            "role": m.role,
                            "content": m.content,
                            "created_at": m.created_at.isoformat()
                            if m.created_at
                            else "",
                        }
                        for m in msgs
                    ],
                }
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def update_ticket(
        self, ticket_id: str, status: str, resolved_at: str | None = None
    ) -> None:
        def _sync():
            db = self._session_sync()
            try:
                t = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
                if t:
                    t.status = status
                    if resolved_at:
                        from datetime import datetime as _dt

                        t.resolved_at = _dt.fromisoformat(
                            resolved_at.replace("Z", "+00:00")
                        )
                    db.commit()
            finally:
                db.close()

        await asyncio.to_thread(_sync)

    async def count_tickets_by_status(self, status: str) -> int:
        def _sync():
            db = self._session_sync()
            try:
                return db.query(Ticket).filter(Ticket.status == status).count()
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    # -- faqs --------------------------------------------------------------

    async def list_faqs(
        self, filters: dict | None = None, page: int = 1, per_page: int = 50
    ) -> dict:
        filters = filters or {}

        def _sync():
            db = self._session_sync()
            try:
                q = db.query(FAQEntry)
                if filters.get("search"):
                    q = q.filter(FAQEntry.question.ilike(f"%{filters['search']}%"))
                total = q.count()
                q = q.order_by(FAQEntry.created_at.desc())
                q = q.offset((page - 1) * per_page).limit(per_page)
                faqs = []
                for f in q.all():
                    faqs.append(
                        {
                            "id": f.id,
                            "question": f.question,
                            "answer": f.answer,
                            "intent_tags": _json.loads(f.intent_tags)
                            if f.intent_tags
                            else [],
                            "created_at": f.created_at.isoformat()
                            if f.created_at
                            else "",
                        }
                    )
                return {"faqs": faqs, "total": total}
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def create_faq(
        self, question: str, answer: str, intent_tags: list[str]
    ) -> dict:
        def _sync():
            db = self._session_sync()
            try:
                entry = FAQEntry(
                    question=question,
                    answer=answer,
                    intent_tags=_json.dumps(intent_tags),
                )
                db.add(entry)
                db.commit()
                db.refresh(entry)
                return {
                    "id": entry.id,
                    "question": entry.question,
                    "answer": entry.answer,
                    "intent_tags": intent_tags,
                    "created_at": entry.created_at.isoformat()
                    if entry.created_at
                    else "",
                }
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def find_faq_by_question(self, question: str) -> dict | None:
        def _sync():
            db = self._session_sync()
            try:
                f = db.query(FAQEntry).filter(FAQEntry.question == question).first()
                if f is None:
                    return None
                return {
                    "id": f.id,
                    "question": f.question,
                    "answer": f.answer,
                    "intent_tags": _json.loads(f.intent_tags) if f.intent_tags else [],
                }
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def get_faq(self, faq_id: int) -> dict | None:
        def _sync():
            db = self._session_sync()
            try:
                f = db.query(FAQEntry).filter(FAQEntry.id == faq_id).first()
                if f is None:
                    return None
                return {
                    "id": f.id,
                    "question": f.question,
                    "answer": f.answer,
                    "intent_tags": _json.loads(f.intent_tags) if f.intent_tags else [],
                }
            finally:
                db.close()

        return await asyncio.to_thread(_sync)

    async def delete_faq(self, faq_id: int) -> None:
        def _sync():
            db = self._session_sync()
            try:
                db.query(FAQEntry).filter(FAQEntry.id == faq_id).delete()
                db.commit()
            finally:
                db.close()

        await asyncio.to_thread(_sync)

    # -- metrics -----------------------------------------------------------

    async def compute_metrics(self, days: int = 7) -> dict:
        def _sync():
            db = self._session_sync()
            try:
                since = datetime.utcnow() - timedelta(days=days)
                total = db.query(Message).filter(Message.created_at >= since).count()
                auto = (
                    db.query(Message)
                    .filter(Message.created_at >= since, Message.auto_answered == 1)
                    .count()
                )
                escalated = (
                    db.query(Ticket)
                    .filter(Ticket.created_at >= since, Ticket.escalated == 1)
                    .count()
                )
                return {
                    "total_conversations": total,
                    "auto_resolved": auto,
                    "escalated": escalated,
                    "avg_handling_time_seconds": 0.0,
                    "csat_score": None,
                    "trends": {},
                    "intent_breakdown": [],
                    "daily_volume": [],
                    "resolution_rate_over_time": [],
                    "top_keywords": [],
                }
            finally:
                db.close()

        return await asyncio.to_thread(_sync)
