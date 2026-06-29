from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from supportai.ml.pipeline_config import PipelineConfig
from supportai.ml.sentiment import SentimentAnalyzer


@pytest.fixture(autouse=True)
def _mock_transformers():
    mock_mod = ModuleType("transformers")
    mock_mod.Pipeline = type("Pipeline", (), {})  # just needs to exist
    old = sys.modules.get("transformers")
    sys.modules["transformers"] = mock_mod
    yield
    if old:
        sys.modules["transformers"] = old
    else:
        del sys.modules["transformers"]


@pytest.fixture
def analyzer() -> SentimentAnalyzer:
    cfg = PipelineConfig()
    return SentimentAnalyzer(cfg)


def _set_model(analyzer: SentimentAnalyzer, results: list) -> None:
    mock = MagicMock()
    mock.side_effect = lambda *a, **kw: results
    analyzer._model = mock


class TestSentimentAnalyzer:
    @pytest.mark.asyncio
    async def test_positive_sentiment(self, analyzer: SentimentAnalyzer):
        _set_model(
            analyzer,
            [
                [
                    {"label": "LABEL_2", "score": 0.92},
                    {"label": "LABEL_1", "score": 0.05},
                    {"label": "LABEL_0", "score": 0.03},
                ]
            ],
        )
        result = await analyzer.analyze("This is amazing! I love it!")
        assert result["sentiment"] == "positive"
        assert result["compound"] > 0.0
        assert result["scores"]["positive"] >= 0.9

    @pytest.mark.asyncio
    async def test_negative_sentiment(self, analyzer: SentimentAnalyzer):
        _set_model(
            analyzer,
            [
                [
                    {"label": "LABEL_0", "score": 0.88},
                    {"label": "LABEL_1", "score": 0.08},
                    {"label": "LABEL_2", "score": 0.04},
                ]
            ],
        )
        result = await analyzer.analyze("This is terrible and frustrating.")
        assert result["sentiment"] == "negative"
        assert result["compound"] < 0.0
        assert result["scores"]["negative"] >= 0.8

    @pytest.mark.asyncio
    async def test_neutral_sentiment(self, analyzer: SentimentAnalyzer):
        _set_model(
            analyzer,
            [
                [
                    {"label": "LABEL_1", "score": 0.90},
                    {"label": "LABEL_0", "score": 0.05},
                    {"label": "LABEL_2", "score": 0.05},
                ]
            ],
        )
        result = await analyzer.analyze("The meeting is at 3pm.")
        assert result["sentiment"] == "neutral"
        assert -0.1 < result["compound"] < 0.1
        assert result["scores"]["neutral"] >= 0.8

    @pytest.mark.asyncio
    async def test_score_normalization(self, analyzer: SentimentAnalyzer):
        _set_model(
            analyzer,
            [
                [
                    {"label": "LABEL_2", "score": 0.70},
                    {"label": "LABEL_1", "score": 0.20},
                    {"label": "LABEL_0", "score": 0.10},
                ]
            ],
        )
        result = await analyzer.analyze("Pretty good experience overall.")
        assert result["scores"]["positive"] == 0.70
        assert result["scores"]["neutral"] == 0.20
        assert result["scores"]["negative"] == 0.10
        assert isinstance(result["timing_ms"], float)
        assert result["timing_ms"] >= 0.0

    @pytest.mark.asyncio
    async def test_empty_message(self, analyzer: SentimentAnalyzer):
        result = await analyzer.analyze("")
        assert result["sentiment"] == "neutral"
        assert result["scores"]["neutral"] == 1.0
        assert result["compound"] == 0.0
        assert result["timing_ms"] == 0.0
