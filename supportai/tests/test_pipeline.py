from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from supportai.ml.pipeline import ChatPipeline
from supportai.ml.pipeline_config import PipelineConfig


@pytest.fixture
def mock_stores() -> dict[str, AsyncMock]:
    return {
        "session_store": AsyncMock(),
        "ticket_store": AsyncMock(),
        "message_store": AsyncMock(),
    }


@pytest.fixture
def pipeline(mock_stores: dict[str, AsyncMock], mock_llm: AsyncMock) -> ChatPipeline:
    cfg = PipelineConfig()
    return ChatPipeline(
        config=cfg,
        session_store=mock_stores["session_store"],
        ticket_store=mock_stores["ticket_store"],
        message_store=mock_stores["message_store"],
        llm_client=mock_llm,
    )


class TestChatPipeline:
    @pytest.mark.asyncio
    async def test_happy_path(self, pipeline: ChatPipeline):
        pipeline._classifier.classify = AsyncMock(
            return_value={
                "intent": "general_inquiry",
                "confidence": 0.95,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
        )
        pipeline._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "auto_answer",
                "faq": {"question": "FAQ?", "answer": "FAQ answer."},
                "score": 0.92,
                "timing_ms": 0.5,
            }
        )
        pipeline._sentiment.analyze = AsyncMock(
            return_value={
                "sentiment": "neutral",
                "scores": {},
                "compound": 0.0,
                "timing_ms": 1.0,
            }
        )
        pipeline._session_store.get_or_create = AsyncMock(return_value="s-happy")
        pipeline._session_store.get = AsyncMock(return_value={"id": "s-happy"})

        result = await pipeline.run("Hello there", session_id="s-happy")
        assert result.success
        assert result.faq_match["match_type"] == "auto_answer"
        assert result.response_text == "FAQ answer."
        assert result.escalation_level == 0
        assert result.total_timing_ms >= 0.0

    @pytest.mark.asyncio
    async def test_session_persistence(self, pipeline: ChatPipeline, mock_stores: dict):
        pipeline._classifier.classify = AsyncMock(
            return_value={
                "intent": "general_inquiry",
                "confidence": 0.95,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
        )
        pipeline._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": 0.5,
            }
        )
        pipeline._sentiment.analyze = AsyncMock(
            return_value={
                "sentiment": "neutral",
                "scores": {},
                "compound": 0.0,
                "timing_ms": 1.0,
            }
        )

        mock_stores["session_store"].get_or_create.return_value = "persisted-session-1"
        mock_stores["session_store"].get.return_value = {"id": "persisted-session-1"}
        mock_stores["message_store"].save = AsyncMock()
        mock_stores["ticket_store"].create = AsyncMock(return_value=False)

        result = await pipeline.run("Hello", session_id="persisted-session-1")
        assert result.success
        assert result.session_id == "persisted-session-1"
        mock_stores["session_store"].get_or_create.assert_awaited_once()
        mock_stores["message_store"].save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_escalation_flow(self, pipeline: ChatPipeline, mock_stores: dict):
        pipeline._classifier.classify = AsyncMock(
            return_value={
                "intent": "technical_issue",
                "confidence": 0.9,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
        )
        pipeline._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": 0.5,
            }
        )
        pipeline._sentiment.analyze = AsyncMock(
            return_value={
                "sentiment": "negative",
                "scores": {"negative": 0.6, "neutral": 0.3, "positive": 0.1},
                "compound": -0.3,
                "timing_ms": 1.0,
            }
        )
        mock_stores["session_store"].get_or_create.return_value = "s-esc"
        mock_stores["session_store"].get.return_value = {"id": "s-esc"}
        mock_stores["ticket_store"].create = AsyncMock(return_value=True)

        result = await pipeline.run("The app keeps crashing!", session_id="s-esc")
        assert result.escalation_level >= 1
        assert result.success

    @pytest.mark.asyncio
    async def test_ticket_creation_on_high_escalation(
        self, pipeline: ChatPipeline, mock_stores: dict
    ):
        pipeline._classifier.classify = AsyncMock(
            return_value={
                "intent": "refund",
                "confidence": 0.95,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
        )
        pipeline._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": 0.5,
            }
        )
        pipeline._sentiment.analyze = AsyncMock(
            return_value={
                "sentiment": "negative",
                "scores": {"negative": 0.8, "neutral": 0.1, "positive": 0.1},
                "compound": -0.7,
                "timing_ms": 1.0,
            }
        )
        mock_stores["session_store"].get_or_create.return_value = "s-ticket"
        mock_stores["session_store"].get.return_value = {"id": "s-ticket"}
        mock_stores["ticket_store"].create = AsyncMock(return_value=True)

        result = await pipeline.run("I want my money back now!", session_id="s-ticket")
        assert result.escalation_level >= 2
        assert result.ticket_created

    @pytest.mark.asyncio
    async def test_step_failure_graceful(self):
        cfg = PipelineConfig()
        p = ChatPipeline(config=cfg)
        p._classifier.classify = AsyncMock(
            side_effect=RuntimeError("Classifier crashed")
        )
        p._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": 0.5,
            }
        )
        p._sentiment.analyze = AsyncMock(
            return_value={
                "sentiment": "neutral",
                "scores": {},
                "compound": 0.0,
                "timing_ms": 1.0,
            }
        )

        result = await p.run("Hello", session_id="s-fail")
        assert not result.success
        assert result.error is not None
        assert len(result.response_text) > 0

    @pytest.mark.asyncio
    async def test_input_validation_empty(self, pipeline: ChatPipeline):
        result = await pipeline.run("", session_id="s-empty")
        assert not result.success
        assert result.error == "Empty or invalid input"
        assert "empty" in result.response_text.lower()

    @pytest.mark.asyncio
    async def test_input_validation_whitespace(self, pipeline: ChatPipeline):
        result = await pipeline.run("   ", session_id="s-ws")
        assert not result.success
        assert result.error == "Empty or invalid input"
