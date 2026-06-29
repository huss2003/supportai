from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUPPORTAI_API_KEYS", "sk-supportai-test,sk-alt-key")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000")
os.environ.setdefault("RATE_LIMIT_WINDOW", "60")
os.environ.setdefault("LLM_TIMEOUT_SECONDS", "5")
os.environ.setdefault("FAQ_AUTO_ANSWER_THRESHOLD", "0.85")
os.environ.setdefault("FAQ_SUGGEST_THRESHOLD", "0.60")


@pytest.fixture
def mock_classifier() -> MagicMock:
    classifier = MagicMock()
    classifier.classify.return_value = {
        "intent": "general_inquiry",
        "confidence": 0.95,
        "all_scores": {"general_inquiry": 0.95, "billing": 0.05},
        "source": "keyword",
        "timing_ms": 1.5,
    }
    return classifier


@pytest.fixture
def mock_faq() -> MagicMock:
    faq = MagicMock()
    faq.match.return_value = {
        "match_type": "auto_answer",
        "faq": {"question": "Test?", "answer": "Test answer."},
        "score": 0.92,
        "timing_ms": 0.5,
    }
    return faq


@pytest.fixture
def mock_sentiment() -> MagicMock:
    sentiment = MagicMock()
    sentiment.analyze.return_value = {
        "sentiment": "neutral",
        "scores": {"negative": 0.1, "neutral": 0.8, "positive": 0.1},
        "compound": 0.0,
        "timing_ms": 1.0,
    }
    return sentiment


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.generate.return_value = "This is an LLM-generated response."
    return llm


@pytest.fixture
def sample_messages() -> dict[str, str]:
    return {
        "refund": "I want a refund for my recent purchase",
        "cancel": "I need to cancel my subscription please",
        "billing": "Why was I billed twice this month?",
        "technical": "The app keeps crashing when I try to log in",
        "account": "I forgot my password and can't log in",
        "feature": "Can you add dark mode to the dashboard?",
        "general": "What is the pricing for the pro plan?",
        "greeting": "Hello, how are you?",
        "farewell": "Goodbye, thanks for your help!",
        "empty": "",
        "whitespace": "   ",
    }


@pytest.fixture
def sample_conversation() -> list[dict[str, Any]]:
    return [
        {"role": "user", "content": "Hello", "created_at": "2026-01-01T00:00:00Z"},
        {
            "role": "assistant",
            "content": "Hi! How can I help?",
            "created_at": "2026-01-01T00:00:01Z",
        },
        {
            "role": "user",
            "content": "I need a refund",
            "created_at": "2026-01-01T00:00:05Z",
        },
    ]


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": "sk-supportai-test"}


@pytest.fixture
def alt_auth_headers() -> dict[str, str]:
    return {"X-API-Key": "sk-alt-key"}


@pytest.fixture
def client_with_mocks() -> Generator[TestClient, None, None]:
    """Create TestClient with lifespan suppressed and state fully mocked."""
    from supportai.app import app

    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = asynccontextmanager(_noop_lifespan)

    mock_db = AsyncMock()
    mock_db.is_connected = MagicMock(return_value=True)
    mock_db.list_tickets.return_value = {"tickets": [], "total": 0}
    mock_db.get_ticket.return_value = None
    mock_db.count_tickets_by_status.return_value = 0
    mock_db.list_faqs.return_value = {"faqs": [], "total": 0}
    mock_db.compute_metrics.return_value = {
        "total_conversations": 10,
        "auto_resolved": 5,
        "escalated": 2,
        "avg_handling_time_seconds": 120.0,
        "csat_score": 4.2,
        "trends": {},
        "intent_breakdown": [],
        "daily_volume": [],
        "resolution_rate_over_time": [],
        "top_keywords": [],
    }
    mock_db.find_faq_by_question.return_value = None
    mock_db.create_faq.return_value = {
        "id": 1,
        "question": "How do I reset my password?",
        "answer": "Go to settings and click reset password.",
        "intent_tags": ["account"],
        "created_at": "2026-01-01T00:00:00Z",
    }
    mock_db.get_faq.return_value = None
    mock_db.delete_faq = AsyncMock()
    mock_db.update_ticket = AsyncMock()
    mock_db.delete_faq = AsyncMock()

    mock_pipeline = AsyncMock()
    mock_pipeline.process.return_value = {
        "session_id": "test-session-123",
        "reply": "I can help with that!",
        "intent": "general_inquiry",
        "intent_confidence": 0.95,
        "faq_match": None,
        "sentiment": {"label": "neutral", "score": 0.0, "normalized_score": 0.0},
        "escalation_offered": False,
        "ticket_created": None,
        "response_method": "template_fallback",
    }

    import time

    app.state.startup_time = time.time()
    app.state.db = mock_db
    app.state.pipeline = mock_pipeline

    with TestClient(app) as client:
        yield client
