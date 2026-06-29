from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PipelineConfig:
    classifier_model: str = "facebook/bart-large-mnli"
    classifier_cache_dir: Optional[str] = None
    classifier_device: str = "cpu"
    classifier_max_candidates: int = 20

    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    sentiment_cache_dir: Optional[str] = None
    sentiment_device: str = "cpu"

    faq_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    faq_cache_dir: Optional[str] = None
    faq_device: str = "cpu"

    faq_auto_answer_threshold: float = 0.85
    faq_suggest_threshold: float = 0.60
    faq_no_match_threshold: float = 0.30

    session_expiry_minutes: int = 60
    max_context_messages: int = 50

    rate_limit_default: int = 100
    rate_limit_window_seconds: int = 60

    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3

    model_load_timeout_seconds: int = 60
    prediction_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> PipelineConfig:
        hf_cache = os.getenv("HF_CACHE_DIR")
        if hf_cache:
            Path(hf_cache).mkdir(parents=True, exist_ok=True)

        return cls(
            classifier_model=os.getenv("CLASSIFIER_MODEL", cls.classifier_model),
            classifier_cache_dir=hf_cache or cls.classifier_cache_dir,
            sentiment_model=os.getenv("SENTIMENT_MODEL", cls.sentiment_model),
            sentiment_cache_dir=hf_cache or cls.sentiment_cache_dir,
            faq_embedding_model=os.getenv(
                "FAQ_EMBEDDING_MODEL", cls.faq_embedding_model
            ),
            faq_cache_dir=hf_cache or cls.faq_cache_dir,
            faq_auto_answer_threshold=float(
                os.getenv(
                    "FAQ_AUTO_ANSWER_THRESHOLD", str(cls.faq_auto_answer_threshold)
                )
            ),
            faq_suggest_threshold=float(
                os.getenv("FAQ_SUGGEST_THRESHOLD", str(cls.faq_suggest_threshold))
            ),
            session_expiry_minutes=int(
                os.getenv("SESSION_EXPIRY_MINUTES", str(cls.session_expiry_minutes))
            ),
            max_context_messages=int(
                os.getenv("MAX_CONTEXT_MESSAGES", str(cls.max_context_messages))
            ),
            rate_limit_default=int(
                os.getenv("RATE_LIMIT_DEFAULT", str(cls.rate_limit_default))
            ),
            rate_limit_window_seconds=int(
                os.getenv("RATE_LIMIT_WINDOW", str(cls.rate_limit_window_seconds))
            ),
            llm_timeout_seconds=int(
                os.getenv("LLM_TIMEOUT_SECONDS", str(cls.llm_timeout_seconds))
            ),
            llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", str(cls.llm_max_retries))),
        )
