from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from supportai.ml.pipeline import ChatPipeline
from supportai.ml.pipeline_config import PipelineConfig


@pytest.fixture
def pipeline() -> ChatPipeline:
    cfg = PipelineConfig()
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="LLM generated response")
    return ChatPipeline(config=cfg, llm_client=llm)


INTENT_TEST_CASES = [
    ("refund", "refund", "refund"),
    ("cancel_subscription", "cancel", "cancel"),
    ("billing", "billing", "billing"),
    ("technical_issue", "technical", "technical"),
    ("account_help", "account", "account"),
    ("feature_request", "feature", "feature"),
    ("greeting", "hello", "greeting"),
    ("farewell", "goodbye", "farewell"),
]


class TestResponseGenerator:
    @pytest.mark.asyncio
    async def test_llm_success(self, pipeline: ChatPipeline):
        result = await pipeline.run("What is the refund policy?", session_id="s1")
        assert result.success
        assert result.response_text == "LLM generated response"
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self):
        cfg = PipelineConfig()
        failing_llm = AsyncMock()
        failing_llm.generate = AsyncMock(side_effect=TimeoutError("LLM timed out"))
        p = ChatPipeline(config=cfg, llm_client=failing_llm)
        result = await p.run("I need a refund", session_id="s2")
        assert result.success
        assert (
            "refund" in result.response_text.lower()
            or "billing" in result.response_text.lower()
            or "noted" in result.response_text.lower()
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_general_inquiry_templates(self, pipeline: ChatPipeline):
        for intent_key, msg, _ in INTENT_TEST_CASES:
            pipeline._classifier.classify = AsyncMock(
                return_value={
                    "intent": intent_key,
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
                    "sentiment": "neutral",
                    "scores": {},
                    "compound": 0.0,
                    "timing_ms": 1.0,
                }
            )
            result = await pipeline.run(msg, session_id=f"s-{intent_key}")
            assert result.success

    @pytest.mark.asyncio
    async def test_negative_sentiment_escalation(self):
        cfg = PipelineConfig()
        p = ChatPipeline(config=cfg)
        p._classifier.classify = AsyncMock(
            return_value={
                "intent": "general_inquiry",
                "confidence": 0.9,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
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
                "sentiment": "negative",
                "scores": {"negative": 0.9, "neutral": 0.05, "positive": 0.05},
                "compound": -0.8,
                "timing_ms": 1.0,
            }
        )
        result = await p.run("This is unacceptable!", session_id="s-neg")
        assert result.escalation_level >= 1
        assert result.success

    @pytest.mark.asyncio
    async def test_faq_auto_answer_injected(self):
        cfg = PipelineConfig()
        p = ChatPipeline(config=cfg)
        p._classifier.classify = AsyncMock(
            return_value={
                "intent": "general_inquiry",
                "confidence": 0.9,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
        )
        p._faq_matcher.match = AsyncMock(
            return_value={
                "match_type": "auto_answer",
                "faq": {
                    "question": "What is refund policy?",
                    "answer": "We offer 30-day refunds.",
                },
                "score": 0.92,
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
        result = await p.run("What is the refund policy?", session_id="s-faq")
        assert result.success
        assert "30-day" in result.response_text

    @pytest.mark.asyncio
    async def test_escalation_level_2_ticket_creation(self):
        cfg = PipelineConfig()
        ticket_store = AsyncMock()
        ticket_store.create = AsyncMock(return_value=True)
        p = ChatPipeline(config=cfg, ticket_store=ticket_store)
        p._classifier.classify = AsyncMock(
            return_value={
                "intent": "refund",
                "confidence": 0.95,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
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
                "sentiment": "negative",
                "scores": {"negative": 0.7, "neutral": 0.2, "positive": 0.1},
                "compound": -0.6,
                "timing_ms": 1.0,
            }
        )
        result = await p.run("Give me my money back!", session_id="s-ticket")
        assert result.escalation_level >= 2
        assert result.ticket_created
        assert result.success

    @pytest.mark.asyncio
    async def test_llm_exception_fallback(self):
        cfg = PipelineConfig()
        failing_llm = AsyncMock()
        failing_llm.generate = AsyncMock(side_effect=RuntimeError("LLM failed"))
        p = ChatPipeline(config=cfg, llm_client=failing_llm)
        result = await p.run("Hello", session_id="s-empty")
        assert result.success
        assert len(result.response_text) > 0

    @pytest.mark.asyncio
    async def test_universal_fallback_for_unknown_intent(self):
        cfg = PipelineConfig()
        p = ChatPipeline(config=cfg)
        p._classifier.classify = AsyncMock(
            return_value={
                "intent": "unknown_intent_xyz",
                "confidence": 0.1,
                "all_scores": {},
                "source": "keyword",
                "timing_ms": 1.0,
            }
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
        result = await p.run("Something completely random", session_id="s-unk")
        assert result.success
        assert len(result.response_text) > 0
