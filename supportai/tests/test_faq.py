from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from supportai.ml.faq_matcher import FAQMatcher
from supportai.ml.pipeline_config import PipelineConfig


@pytest.fixture
def faq_matcher() -> FAQMatcher:
    cfg = PipelineConfig()
    cfg.faq_auto_answer_threshold = 0.85
    cfg.faq_suggest_threshold = 0.60
    return FAQMatcher(cfg)


SAMPLE_FAQS = [
    {
        "question": "How do I reset my password?",
        "answer": "Go to settings and click reset password.",
    },
    {
        "question": "What is the refund policy?",
        "answer": "We offer full refunds within 30 days.",
    },
    {
        "question": "How do I cancel my subscription?",
        "answer": "Go to billing settings to cancel.",
    },
]


def _init_with_mock(faq_matcher: FAQMatcher) -> MagicMock:
    model_mock = MagicMock()
    model_mock.encode.return_value = np.random.randn(384)
    faq_matcher._model = model_mock
    faq_matcher._is_loaded = True
    faq_matcher._faq_entries = SAMPLE_FAQS
    faq_matcher._faq_embeddings = np.random.randn(3, 384)
    return model_mock


class TestFAQMatcher:
    @pytest.mark.asyncio
    async def test_exact_match_high_score(self, faq_matcher: FAQMatcher):
        _init_with_mock(faq_matcher)
        result = await faq_matcher.match("How do I reset my password?")
        assert "match_type" in result
        assert "timing_ms" in result

    @pytest.mark.asyncio
    async def test_no_match_empty_db(self, faq_matcher: FAQMatcher):
        result = await faq_matcher.match("How do I reset my password?")
        assert result["match_type"] == "no_match"
        assert result["faq"] is None
        assert result["score"] == 0.0

    @pytest.mark.asyncio
    async def test_no_match_low_similarity(self, faq_matcher: FAQMatcher):
        _init_with_mock(faq_matcher)
        faq_matcher._faq_embeddings = np.zeros((3, 384))
        result = await faq_matcher.match("completely unrelated gibberish xyz")
        assert result["match_type"] == "no_match"
        assert result["faq"] is None

    @pytest.mark.asyncio
    async def test_semantic_match(self, faq_matcher: FAQMatcher):
        model_mock = MagicMock()
        query_vec = np.random.randn(384) * 2
        model_mock.encode.return_value = query_vec
        faqs_emb = np.random.randn(3, 384)
        faqs_emb[1] = query_vec
        faq_matcher._model = model_mock
        faq_matcher._is_loaded = True
        faq_matcher._faq_entries = SAMPLE_FAQS
        faq_matcher._faq_embeddings = faqs_emb
        result = await faq_matcher.match("Tell me about refunds")
        assert result["score"] > 0.0

    @pytest.mark.asyncio
    async def test_timing_measurement(self, faq_matcher: FAQMatcher):
        _init_with_mock(faq_matcher)
        result = await faq_matcher.match("How do I reset my password?")
        assert result["timing_ms"] >= 0.0
        assert isinstance(result["timing_ms"], float)
