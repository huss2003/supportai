from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestChatAPI:
    def test_chat_new_session(self, client_with_mocks: TestClient, auth_headers: dict):
        resp = client_with_mocks.post(
            "/api/chat", json={"message": "Hello"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["reply"] != ""
        assert data["intent"] is not None

    def test_chat_with_existing_session(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.post(
            "/api/chat",
            json={
                "session_id": "existing-session",
                "message": "I need help",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] is not None

    def test_chat_empty_message(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.post(
            "/api/chat", json={"message": ""}, headers=auth_headers
        )
        assert resp.status_code in (400, 422)

    def test_chat_missing_message(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.post("/api/chat", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_chat_with_metadata(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.post(
            "/api/chat",
            json={
                "message": "Hello",
                "metadata": {"source": "web", "page": "pricing"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_chat_no_auth(self, client_with_mocks: TestClient):
        resp = client_with_mocks.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 401


class TestTicketAPI:
    def test_list_tickets(self, client_with_mocks: TestClient, auth_headers: dict):
        resp = client_with_mocks.get("/api/tickets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data
        assert "pagination" in data

    def test_list_tickets_with_filters(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.get(
            "/api/tickets?status=open&page=1&per_page=10", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_get_ticket_not_found(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.get(
            "/api/tickets/nonexistent-123", headers=auth_headers
        )
        assert resp.status_code == 404

    def test_get_ticket_requires_auth(self, client_with_mocks: TestClient):
        resp = client_with_mocks.get("/api/tickets")
        assert resp.status_code == 401

    def test_update_ticket_status(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        from supportai.app import app

        mock_db = AsyncMock()
        mock_db.get_ticket.return_value = {
            "ticket_id": "tkt-001",
            "session_id": "s1",
            "intent": "billing",
            "priority_score": 3,
            "priority_breakdown": {},
            "status": "open",
            "escalated": True,
            "conversation": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "resolved_at": None,
        }
        mock_db.update_ticket = AsyncMock()
        app.state.db = mock_db
        app.state.pipeline = AsyncMock()
        app.state.pipeline.process = AsyncMock(
            return_value={
                "session_id": "s1",
                "reply": "ok",
                "intent": "billing",
                "intent_confidence": 0.9,
                "faq_match": None,
                "sentiment": {
                    "label": "neutral",
                    "score": 0.0,
                    "normalized_score": 0.0,
                },
                "escalation_offered": False,
                "ticket_created": None,
                "response_method": "fallback",
            }
        )

        resp = client_with_mocks.patch(
            "/api/tickets/tkt-001", json={"status": "in_progress"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"

    def test_update_ticket_not_found(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        resp = client_with_mocks.patch(
            "/api/tickets/nonexistent",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestFAQAPI:
    def test_list_faqs(self, client_with_mocks: TestClient, auth_headers: dict):
        resp = client_with_mocks.get("/api/faq", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "faqs" in data
        assert "pagination" in data

    def test_create_faq(self, client_with_mocks: TestClient, auth_headers: dict):
        from supportai.app import app

        mock_db = AsyncMock()
        mock_db.find_faq_by_question.return_value = None
        mock_db.create_faq.return_value = {
            "id": 1,
            "question": "How do I reset my password?",
            "answer": "Go to settings and click reset password.",
            "intent_tags": ["account"],
            "created_at": "2026-01-01T00:00:00Z",
        }
        app.state.db = mock_db

        resp = client_with_mocks.post(
            "/api/faq",
            json={
                "question": "How do I reset my password?",
                "answer": "Go to settings and click reset password.",
                "intent_tags": ["account"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["question"] == "How do I reset my password?"

    def test_create_faq_duplicate(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        from supportai.app import app

        mock_db = AsyncMock()
        mock_db.find_faq_by_question.return_value = {
            "id": 1,
            "question": "test",
            "answer": "test answer",
        }
        app.state.db = mock_db

        resp = client_with_mocks.post(
            "/api/faq",
            json={
                "question": "How do I reset my password?",
                "answer": "Go to settings and click reset password.",
                "intent_tags": ["account"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_delete_faq(self, client_with_mocks: TestClient, auth_headers: dict):
        from supportai.app import app

        mock_db = AsyncMock()
        mock_db.get_faq.return_value = {
            "id": 1,
            "question": "test",
            "answer": "test answer",
        }
        mock_db.delete_faq = AsyncMock()
        app.state.db = mock_db

        resp = client_with_mocks.delete("/api/faq/1", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_faq_not_found(
        self, client_with_mocks: TestClient, auth_headers: dict
    ):
        from supportai.app import app

        mock_db = AsyncMock()
        mock_db.get_faq.return_value = None
        app.state.db = mock_db

        resp = client_with_mocks.delete("/api/faq/999", headers=auth_headers)
        assert resp.status_code == 404


class TestAdminAPI:
    def test_admin_metrics(self, client_with_mocks: TestClient, auth_headers: dict):
        resp = client_with_mocks.get("/api/admin/metrics?days=7", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_conversations" in data
        assert "auto_resolved" in data
        assert "escalated" in data
        assert data["total_conversations"] == 10


class TestHealthAPI:
    def test_health_check(self, client_with_mocks: TestClient):
        resp = client_with_mocks.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "uptime_seconds" in data


class TestSecurity:
    def test_invalid_api_key(self, client_with_mocks: TestClient):
        resp = client_with_mocks.get(
            "/api/tickets", headers={"X-API-Key": "invalid-key"}
        )
        assert resp.status_code == 401

    def test_missing_api_key(self, client_with_mocks: TestClient):
        resp = client_with_mocks.get("/api/tickets")
        assert resp.status_code == 401
