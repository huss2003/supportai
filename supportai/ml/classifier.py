from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Optional

import numpy as np

from supportai.ml.pipeline_config import PipelineConfig

logger = logging.getLogger(__name__)

INTENT_KEYWORD_MAP: dict[str, list[str]] = {
    "refund": [
        "refund",
        "money back",
        "reimburs",
        "chargeback",
        "return my money",
        "i want my money",
        "give me my money back",
        "credit my account",
        "reverse the charge",
        "issue a refund",
    ],
    "cancel_subscription": [
        "cancel",
        "unsubscribe",
        "stop subscription",
        "end my plan",
        "terminate",
        "i want to cancel",
        "cancel my account",
        "do not renew",
        "turn off auto-renew",
        "cancel membership",
    ],
    "billing": [
        "billing",
        "invoice",
        "receipt",
        "overcharged",
        "double charge",
        "billed twice",
        "wrong amount",
        "payment issue",
        "card declined",
        "charge on my card",
        "billing address",
        "tax on my",
    ],
    "technical_issue": [
        "error",
        "bug",
        "crash",
        "not working",
        "loading",
        "blank screen",
        "freeze",
        "stuck",
        "timeout",
        "error message",
        "error code",
        "broken",
        "fetch",
        "get error",
        "not loading",
        "won't load",
    ],
    "account_help": [
        "login",
        "password",
        "reset",
        "forgot",
        "sign in",
        "can't log",
        "locked out",
        "change password",
        "update profile",
        "change email",
        "username",
        "two-factor",
        "2fa",
        "mfa",
        "disable account",
    ],
    "feature_request": [
        "feature request",
        "add feature",
        "i wish",
        "would be nice if",
        "can you add",
        "new functionality",
        "enhancement",
        "could you implement",
        "suggestion",
        "feature suggestion",
        "please add",
        "would love",
    ],
    "general_inquiry": [
        "how does",
        "what is",
        "tell me about",
        "pricing",
        "plan",
        "compare",
        "versus",
        "difference between",
        "can you explain",
        "i have a question about",
        "how to",
        "how do i",
    ],
    "greeting": [
        "hello",
        "hi ",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
        "what's up",
        "yo",
    ],
    "farewell": [
        "goodbye",
        "bye",
        "see you",
        "thanks for your help",
        "that is all",
        "i am done",
        "have a good day",
    ],
}


class IntentClassifier:
    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._candidate_labels: list[str] = [
            "refund",
            "cancel subscription",
            "billing question",
            "technical issue",
            "account help",
            "feature request",
            "general inquiry",
            "greeting",
            "farewell",
        ]

    def _load_model(self) -> None:
        if self._model is not None:
            return
        start = time.monotonic()
        try:
            from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]

            self._model = hf_pipeline(
                "zero-shot-classification",
                model=self._config.classifier_model,
                cache_dir=self._config.classifier_cache_dir,
                device=self._config.classifier_device,
            )
            logger.info(
                "Zero-shot model loaded in %.2fs",
                time.monotonic() - start,
            )
        except Exception:
            logger.exception("Failed to load zero-shot model; keyword fallback only")
            self._model = None

    def _keyword_score(self, text: str) -> dict[str, float]:
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for intent, keywords in INTENT_KEYWORD_MAP.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 1.0
            if score > 0:
                scores[intent] = min(
                    score / max(1.0, max(len(keywords) * 0.3, 1.0)), 1.0
                )

        if not scores:
            scores["general_inquiry"] = 0.5
        return scores

    async def classify(
        self,
        text: str,
        multi_label: bool = False,
    ) -> dict[str, Any]:
        if not text or not text.strip():
            return {
                "intent": "general_inquiry",
                "confidence": 1.0,
                "all_scores": {"general_inquiry": 1.0},
                "source": "fallback",
                "timing_ms": 0.0,
            }

        start = time.monotonic()
        keyword_scores = self._keyword_score(text)
        keyword_top = max(keyword_scores, key=keyword_scores.get)

        self._load_model()
        if self._model is None:
            elapsed = (time.monotonic() - start) * 1000
            return {
                "intent": keyword_top,
                "confidence": keyword_scores[keyword_top],
                "all_scores": keyword_scores,
                "source": "keyword",
                "timing_ms": round(elapsed, 1),
            }

        try:
            result = await asyncio.to_thread(
                self._model,
                text,
                candidate_labels=self._candidate_labels,
                multi_label=multi_label,
            )
            zs_scores: dict[str, float] = dict(zip(result["labels"], result["scores"]))
            zs_top = result["labels"][0]
            zs_conf = float(result["scores"][0])

            best_by_source: list[tuple[str, str, float]] = [
                ("zero-shot", zs_top, zs_conf),
                ("keyword", keyword_top, keyword_scores[keyword_top]),
            ]
            best_source, best_intent, best_conf = max(
                best_by_source, key=lambda x: x[2]
            )

            if best_source == "keyword" and best_conf > 0.7:
                combined_intent = best_intent
                combined_conf = best_conf
            else:
                combined_intent = zs_top
                combined_conf = zs_conf

            elapsed = (time.monotonic() - start) * 1000
            return {
                "intent": combined_intent,
                "confidence": round(combined_conf, 4),
                "all_scores": zs_scores,
                "keyword_scores": keyword_scores,
                "source": best_source,
                "timing_ms": round(elapsed, 1),
            }
        except Exception:
            logger.exception("Zero-shot classification failed; using keyword fallback")
            elapsed = (time.monotonic() - start) * 1000
            return {
                "intent": keyword_top,
                "confidence": keyword_scores[keyword_top],
                "all_scores": keyword_scores,
                "source": "keyword_fallback",
                "timing_ms": round(elapsed, 1),
            }
