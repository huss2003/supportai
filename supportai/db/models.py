import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    LargeBinary,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    escalation_state: Mapped[str] = mapped_column(
        String, default="normal", nullable=False
    )
    negative_message_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    active_ticket_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(
        "metadata", Text, nullable=True
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="session", cascade="all, delete-orphan"
    )
    feedback_entries: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'expired')", name="ck_session_status"),
        CheckConstraint(
            "escalation_state IN ('normal', 'escalation_offered', 'declined', 'escalated', 'auto_escalated')",
            name="ck_session_escalation_state",
        ),
        CheckConstraint(
            "negative_message_count >= 0",
            name="ck_negative_msg_count",
        ),
        Index("idx_sessions_last_active", "last_active_at"),
    )

    def __repr__(self) -> str:
        return f"<Session(session_id='{self.session_id}', status='{self.status}')>"

    @property
    def metadata_dict(self) -> Optional[dict]:
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @metadata_dict.setter
    def metadata_dict(self, value: Optional[dict]) -> None:
        if value is not None:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = None


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.session_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    secondary_intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faq_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    faq_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faq_entries.id"), nullable=True
    )
    faq_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timing_classification_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    timing_faq_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timing_sentiment_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timing_generation_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timing_total_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    faq_entry: Mapped[Optional["FAQEntry"]] = relationship(
        "FAQEntry", back_populates="messages"
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name="ck_message_role"
        ),
        CheckConstraint(
            "intent IN ('billing', 'technical', 'account', 'general', 'unknown')",
            name="ck_message_intent",
        ),
        CheckConstraint(
            "method IN ('llm', 'template_fallback', 'keyword_fallback')",
            name="ck_message_method",
        ),
        CheckConstraint(
            "sentiment IN ('positive', 'neutral', 'negative')",
            name="ck_message_sentiment",
        ),
        Index("idx_messages_session", "session_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, session_id='{self.session_id}', "
            f"role='{self.role}', intent='{self.intent}')>"
        )


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.session_id"), nullable=False
    )
    intent: Mapped[str] = mapped_column(String, nullable=False)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_breakdown: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    escalated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auto_escalated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="tickets")

    __table_args__ = (
        CheckConstraint(
            "priority_score >= 1 AND priority_score <= 5",
            name="ck_ticket_priority_score",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved')",
            name="ck_ticket_status",
        ),
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_priority", "priority_score"),
        Index("idx_tickets_session", "session_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Ticket(ticket_id='{self.ticket_id}', status='{self.status}', "
            f"priority={self.priority_score})>"
        )

    @property
    def priority_breakdown_dict(self) -> dict:
        if self.priority_breakdown:
            try:
                return json.loads(self.priority_breakdown)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @priority_breakdown_dict.setter
    def priority_breakdown_dict(self, value: dict) -> None:
        self.priority_breakdown = json.dumps(value)


class FAQEntry(Base):
    __tablename__ = "faq_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    intent_tags: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="faq_entry"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FAQEntry(id={self.id}, question='{self.question[:50]}...')>"

    @property
    def intent_tags_list(self) -> list:
        if self.intent_tags:
            try:
                return json.loads(self.intent_tags)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @intent_tags_list.setter
    def intent_tags_list(self, value: list) -> None:
        self.intent_tags = json.dumps(value)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.session_id"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    session: Mapped["Session"] = relationship(
        "Session", back_populates="feedback_entries"
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating"),
    )

    def __repr__(self) -> str:
        return (
            f"<Feedback(id={self.id}, session_id='{self.session_id}', "
            f"rating={self.rating})>"
        )
