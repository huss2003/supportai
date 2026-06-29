from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import numpy as np

from supportai.ml.pipeline_config import PipelineConfig

logger = logging.getLogger(__name__)


class FAQMatcher:
    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._model: Optional[Any] = None
        self._faq_embeddings: Optional[np.ndarray] = None
        self._faq_entries: list[dict[str, str]] = []
        self._is_loaded: bool = False

    def _load_model(self) -> None:
        if self._is_loaded:
            return
        start = time.monotonic()
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            self._model = SentenceTransformer(
                self._config.faq_embedding_model,
                cache_folder=self._config.faq_cache_dir,
                device=self._config.faq_device,
            )
            logger.info(
                "FAQ embedding model loaded in %.2fs",
                time.monotonic() - start,
            )
        except Exception:
            logger.exception("Failed to load FAQ embedding model")
            self._model = None

    def index_faqs(self, faqs: list[dict[str, str]]) -> None:
        self._faq_entries = faqs
        self._load_model()
        if self._model is None or not faqs:
            self._faq_embeddings = None
            return
        start = time.monotonic()
        questions = [f["question"] for f in faqs]
        try:
            self._faq_embeddings = self._model.encode(
                questions, convert_to_numpy=True, show_progress_bar=False
            )
            logger.info(
                "Indexed %d FAQs in %.2fs",
                len(faqs),
                time.monotonic() - start,
            )
        except Exception:
            logger.exception("Failed to encode FAQ questions")
            self._faq_embeddings = None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = a / (np.linalg.norm(a) + 1e-12)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
        return np.dot(a_norm, b_norm.T).flatten()

    async def match(self, text: str) -> dict[str, Any]:
        start = time.monotonic()

        if not text or not text.strip():
            return {
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": 0.0,
            }

        if not self._faq_entries or self._faq_embeddings is None:
            return {
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": round((time.monotonic() - start) * 1000, 1),
            }

        self._load_model()
        if self._model is None:
            return {
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": round((time.monotonic() - start) * 1000, 1),
            }

        try:
            query_vec = await asyncio.to_thread(
                self._model.encode, text, convert_to_numpy=True, show_progress_bar=False
            )
            similarities = self._cosine_similarity(query_vec, self._faq_embeddings)
            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])

            elapsed = (time.monotonic() - start) * 1000

            if best_score >= self._config.faq_auto_answer_threshold:
                match_type = "auto_answer"
            elif best_score >= self._config.faq_suggest_threshold:
                match_type = "suggestion"
            else:
                match_type = "no_match"

            entry = self._faq_entries[best_idx] if match_type != "no_match" else None

            return {
                "match_type": match_type,
                "faq": entry,
                "score": round(best_score, 4),
                "timing_ms": round(elapsed, 1),
            }
        except Exception:
            logger.exception("FAQ matching failed")
            elapsed = (time.monotonic() - start) * 1000
            return {
                "match_type": "no_match",
                "faq": None,
                "score": 0.0,
                "timing_ms": round(elapsed, 1),
            }
