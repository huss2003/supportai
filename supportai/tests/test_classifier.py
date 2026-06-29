from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from supportai.ml.classifier import IntentClassifier
from supportai.ml.pipeline_config import PipelineConfig


@pytest.fixture
def classifier() -> IntentClassifier:
    cfg = PipelineConfig()
    cfg.classifier_model = "facebook/bart-large-mnli"
    return IntentClassifier(cfg)


class TestIntentClassifier:
    @pytest.mark.asyncio
    async def test_classify_refund_intent(self, classifier: IntentClassifier):
        result = await classifier.classify("I want a refund for my recent purchase")
        assert result["intent"] == "refund"
        assert result["confidence"] > 0.0
        assert result["source"] in ("keyword", "keyword_fallback", "zero-shot")

    @pytest.mark.asyncio
    async def test_classify_cancel_intent(self, classifier: IntentClassifier):
        result = await classifier.classify("Please cancel my subscription immediately")
        assert result["intent"] in ("cancel_subscription", "cancel subscription")
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_classify_billing_intent(self, classifier: IntentClassifier):
        result = await classifier.classify("I was overcharged on my invoice")
        assert result["intent"] == "billing"
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_classify_technical_intent(self, classifier: IntentClassifier):
        result = await classifier.classify("The app keeps crashing when I open it")
        assert result["intent"] == "technical_issue"
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_classify_low_confidence_fallback(self, classifier: IntentClassifier):
        result = await classifier.classify("purple elephant rainbow")
        assert result["intent"] == "general_inquiry"
        assert result["confidence"] >= 0.5
        assert result["source"] in ("keyword", "keyword_fallback", "zero-shot")

    @pytest.mark.asyncio
    async def test_classify_empty_input(self, classifier: IntentClassifier):
        result = await classifier.classify("")
        assert result["intent"] == "general_inquiry"
        assert result["confidence"] == 1.0
        assert result["source"] == "fallback"

    @pytest.mark.asyncio
    async def test_classify_whitespace_input(self, classifier: IntentClassifier):
        result = await classifier.classify("   ")
        assert result["intent"] == "general_inquiry"
        assert result["confidence"] == 1.0
        assert result["source"] == "fallback"

    @pytest.mark.asyncio
    async def test_classify_truncation_long_text(self, classifier: IntentClassifier):
        long = "refund " * 500
        result = await classifier.classify(long)
        assert result["intent"] != "general_inquiry"

    @pytest.mark.asyncio
    async def test_classify_keyword_fallback_on_model_failure(self):
        cfg = PipelineConfig()
        cfg.classifier_model = "non-existent-model-xyz"
        c = IntentClassifier(cfg)
        result = await c.classify("I need a refund")
        assert result["intent"] == "refund"
        assert result["source"] == "keyword"
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_classify_timing_measurement(self, classifier: IntentClassifier):
        result = await classifier.classify("Hello, how are you?")
        assert result["timing_ms"] >= 0.0
        assert isinstance(result["timing_ms"], float)

    @pytest.mark.asyncio
    async def test_classify_keyword_score_for_matched_text(
        self, classifier: IntentClassifier
    ):
        result = await classifier.classify(
            "This is a bug, it crashes and gives an error"
        )
        assert result["intent"] == "technical_issue"
        assert result["confidence"] > 0.0
        assert "timing_ms" in result

    @pytest.mark.asyncio
    async def test_classify_secondary_intent_in_all_scores(
        self, classifier: IntentClassifier
    ):
        result = await classifier.classify("Hello there")
        if "all_scores" in result:
            assert "greeting" in result["all_scores"]
            assert result["all_scores"]["greeting"] >= 0.0
