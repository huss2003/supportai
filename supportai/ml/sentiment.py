from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import numpy as np

from supportai.ml.pipeline_config import PipelineConfig

logger = logging.getLogger(__name__)

LABEL_MAP: dict[str, str] = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
}


class SentimentAnalyzer:
    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        start = time.monotonic()
        try:
            from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]

            self._model = hf_pipeline(
                "sentiment-analysis",
                model=self._config.sentiment_model,
                cache_dir=self._config.sentiment_cache_dir,
                device=self._config.sentiment_device,
                truncation=True,
                max_length=512,
            )
            logger.info(
                "Sentiment model loaded in %.2fs",
                time.monotonic() - start,
            )
        except Exception:
            logger.exception("Failed to load sentiment model")
            self._model = None

    def _normalize_scores(self, raw: list[dict[str, Any]]) -> dict[str, float]:
        scores: dict[str, float] = {"negative": 0.0, "neutral": 0.0, "positive": 0.0}
        for item in raw:
            label = LABEL_MAP.get(item["label"], item["label"].lower())
            scores[label] = float(item["score"])
        return scores

    async def analyze(self, text: str) -> dict[str, Any]:
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "scores": {"negative": 0.0, "neutral": 1.0, "positive": 0.0},
                "compound": 0.0,
                "timing_ms": 0.0,
            }

        start = time.monotonic()
        self._load_model()

        if self._model is None:
            elapsed = (time.monotonic() - start) * 1000
            return {
                "sentiment": "neutral",
                "scores": {"negative": 0.0, "neutral": 1.0, "positive": 0.0},
                "compound": 0.0,
                "timing_ms": round(elapsed, 1),
            }

        try:
            from transformers import Pipeline as HFPipeline  # type: ignore[import-untyped]

            pipe: HFPipeline = self._model
            result = await asyncio.to_thread(
                pipe, text, return_all_scores=True, truncation=True
            )
            scores = self._normalize_scores(result[0])

            compound = scores["positive"] - scores["negative"]
            sentiment: str = (
                "positive"
                if scores["positive"] > scores["negative"]
                and scores["positive"] > scores["neutral"]
                else "negative"
                if scores["negative"] > scores["positive"]
                and scores["negative"] > scores["neutral"]
                else "neutral"
            )

            elapsed = (time.monotonic() - start) * 1000
            return {
                "sentiment": sentiment,
                "scores": scores,
                "compound": round(compound, 4),
                "timing_ms": round(elapsed, 1),
            }
        except Exception:
            logger.exception("Sentiment analysis failed")
            elapsed = (time.monotonic() - start) * 1000
            return {
                "sentiment": "neutral",
                "scores": {"negative": 0.0, "neutral": 1.0, "positive": 0.0},
                "compound": 0.0,
                "timing_ms": round(elapsed, 1),
            }
