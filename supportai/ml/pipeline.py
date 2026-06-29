from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from supportai.ml.classifier import IntentClassifier
from supportai.ml.faq_matcher import FAQMatcher
from supportai.ml.pipeline_config import PipelineConfig
from supportai.ml.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    success: bool
    session_id: Optional[str]
    user_message: str
    intent: dict[str, Any]
    faq_match: dict[str, Any]
    sentiment: dict[str, Any]
    escalation_level: int
    response_text: str
    ticket_created: bool
    steps: dict[str, Any] = field(default_factory=dict)
    total_timing_ms: float = 0.0
    error: Optional[str] = None


class ChatPipeline:
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        session_store: Optional[Any] = None,
        ticket_store: Optional[Any] = None,
        message_store: Optional[Any] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        self._config = config or PipelineConfig.from_env()
        self._classifier = IntentClassifier(self._config)
        self._faq_matcher = FAQMatcher(self._config)
        self._sentiment = SentimentAnalyzer(self._config)
        self._session_store = session_store
        self._ticket_store = ticket_store
        self._message_store = message_store
        self._llm_client = llm_client

    def _step(self, name: str, timing: dict[str, float]) -> None:
        timing["_last"] = time.monotonic()

    def _elapsed(self, name: str, timing: dict[str, float]) -> float:
        now = time.monotonic()
        start = timing.get("_last", timing.get("_start", now))
        return round((now - start) * 1000, 1)

    def index_faqs(self, faqs: list[dict[str, str]]) -> None:
        self._faq_matcher.index_faqs(faqs)

    async def run(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        channel: str = "chat",
        user_id: Optional[str] = None,
    ) -> PipelineResult:
        timing: dict[str, float] = {"_start": time.monotonic()}
        steps: dict[str, Any] = {}
        escalation_level: int = 0
        ticket_created: bool = False
        response_text: str = ""

        step_order = [
            "validate_input",
            "get_session",
            "classify_intent",
            "match_faq",
            "analyze_sentiment",
            "update_escalation",
            "generate_response",
            "create_ticket",
            "save_messages",
            "build_response",
        ]
        step_timings: dict[str, float] = {}

        try:
            # step 1 — validate input
            self._step("validate_input", timing)
            if not user_message or not user_message.strip():
                raise ValueError("user_message is empty")
            cleaned = user_message.strip()
            step_timings["validate_input"] = self._elapsed("validate_input", timing)

            # step 2 — get or create session
            self._step("get_session", timing)
            resolved_session_id = session_id
            if self._session_store is not None:
                resolved_session_id = await self._session_store.get_or_create(
                    session_id=session_id, user_id=user_id, channel=channel
                )
            step_timings["get_session"] = self._elapsed("get_session", timing)

            # step 3 — classify intent
            self._step("classify_intent", timing)
            intent_result = await self._classifier.classify(cleaned)
            steps["classify_intent"] = {
                "intent": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "source": intent_result.get("source", "unknown"),
            }
            step_timings["classify_intent"] = self._elapsed("classify_intent", timing)

            # step 4 — match FAQ
            self._step("match_faq", timing)
            faq_result = await self._faq_matcher.match(cleaned)
            steps["match_faq"] = {
                "match_type": faq_result["match_type"],
                "score": faq_result["score"],
            }
            step_timings["match_faq"] = self._elapsed("match_faq", timing)

            # step 5 — analyze sentiment
            self._step("analyze_sentiment", timing)
            sentiment_result = await self._sentiment.analyze(cleaned)
            steps["analyze_sentiment"] = {
                "sentiment": sentiment_result["sentiment"],
                "compound": sentiment_result["compound"],
            }
            step_timings["analyze_sentiment"] = self._elapsed(
                "analyze_sentiment", timing
            )

            # step 6 — update escalation level and persist state
            self._step("update_escalation", timing)
            escalation_level = self._compute_escalation(
                intent_result, sentiment_result, faq_result
            )
            if self._session_store is not None:
                sid_data = await self._session_store.get(resolved_session_id)
                if sid_data is not None:
                    if escalation_level >= 2:
                        sid_data["escalation_state"] = "auto_escalated"
                    elif escalation_level == 1:
                        sid_data["escalation_state"] = sid_data.get(
                            "escalation_state", "normal"
                        )
                    else:
                        sid_data["escalation_state"] = "normal"
            step_timings["update_escalation"] = self._elapsed(
                "update_escalation", timing
            )

            # step 7 — generate response
            self._step("generate_response", timing)
            response_text = await self._generate_response(
                cleaned,
                intent_result,
                faq_result,
                sentiment_result,
                escalation_level,
            )
            step_timings["generate_response"] = self._elapsed(
                "generate_response", timing
            )

            # step 8 — create ticket if escalation threshold met (with dedup)
            self._step("create_ticket", timing)
            session_data = (
                await self._session_store.get(resolved_session_id)
                if self._session_store
                else None
            )
            has_ticket = bool(session_data and session_data.get("active_ticket_id"))
            if (
                escalation_level >= 2
                and self._ticket_store is not None
                and not has_ticket
            ):
                ticket_created = await self._ticket_store.create(
                    user_message=cleaned,
                    intent=intent_result["intent"],
                    sentiment=sentiment_result["sentiment"],
                    escalation_level=escalation_level,
                    session_id=resolved_session_id,
                    user_id=user_id,
                    channel=channel,
                )
                if ticket_created and self._session_store is not None:
                    sid_data = await self._session_store.get(resolved_session_id)
                    if sid_data is not None:
                        sid_data["active_ticket_id"] = True
            step_timings["create_ticket"] = self._elapsed("create_ticket", timing)

            # step 9 — save messages to session store
            self._step("save_messages", timing)
            if self._message_store is not None:
                await self._message_store.save(
                    session_id=resolved_session_id,
                    user_message=cleaned,
                    response=response_text,
                    intent=intent_result["intent"],
                    sentiment=sentiment_result["sentiment"],
                    channel=channel,
                )
            step_timings["save_messages"] = self._elapsed("save_messages", timing)

            # step 10 — build final response
            self._step("build_response", timing)
            step_timings["build_response"] = self._elapsed("build_response", timing)

            total = round((time.monotonic() - timing["_start"]) * 1000, 1)

            return PipelineResult(
                success=True,
                session_id=resolved_session_id,
                user_message=cleaned,
                intent=intent_result,
                faq_match=faq_result,
                sentiment=sentiment_result,
                escalation_level=escalation_level,
                response_text=response_text,
                ticket_created=ticket_created,
                steps=steps,
                total_timing_ms=total,
            )

        except ValueError:
            logger.exception("Input validation failed")
            return PipelineResult(
                success=False,
                session_id=session_id,
                user_message=user_message or "",
                intent={"intent": "unknown", "confidence": 0.0},
                faq_match={"match_type": "no_match", "faq": None, "score": 0.0},
                sentiment={
                    "sentiment": "neutral",
                    "scores": {},
                    "compound": 0.0,
                },
                escalation_level=0,
                response_text="I received an empty message. Please type your question.",
                ticket_created=False,
                error="Empty or invalid input",
            )
        except Exception:
            logger.exception("Pipeline run failed")
            return PipelineResult(
                success=False,
                session_id=session_id,
                user_message=user_message or "",
                intent={"intent": "unknown", "confidence": 0.0},
                faq_match={"match_type": "no_match", "faq": None, "score": 0.0},
                sentiment={
                    "sentiment": "neutral",
                    "scores": {},
                    "compound": 0.0,
                },
                escalation_level=0,
                response_text="Sorry, something went wrong. Please try again or contact support.",
                ticket_created=False,
                error="Pipeline internal error",
            )

    def _compute_escalation(
        self,
        intent_result: dict[str, Any],
        sentiment_result: dict[str, Any],
        faq_result: dict[str, Any],
    ) -> int:
        level = 0

        high_priority_intents = {"refund", "cancel_subscription", "billing"}
        if intent_result.get("intent") in high_priority_intents:
            level = max(level, 2)

        if intent_result.get("intent") == "technical_issue":
            level = max(level, 1)

        sentiment = sentiment_result.get("sentiment", "neutral")
        compound = sentiment_result.get("compound", 0.0)
        if sentiment == "negative" and compound < -0.5:
            level = max(level, 2)
        elif sentiment == "negative":
            level = max(level, 1)

        if faq_result.get("match_type") == "no_match":
            level = max(level, 1)

        if (
            intent_result.get("confidence", 1.0) < 0.3
            and faq_result.get("match_type") == "no_match"
        ):
            level = max(level, 1)

        return level

    async def _generate_response(
        self,
        cleaned: str,
        intent_result: dict[str, Any],
        faq_result: dict[str, Any],
        sentiment_result: dict[str, Any],
        escalation_level: int,
    ) -> str:
        if faq_result.get("match_type") == "auto_answer":
            faq = faq_result.get("faq")
            if faq and faq.get("answer"):
                return faq["answer"]

        if self._llm_client is not None:
            try:
                return await self._llm_client.generate(
                    message=cleaned,
                    intent=intent_result.get("intent", "unknown"),
                    sentiment=sentiment_result.get("sentiment", "neutral"),
                    escalation_level=escalation_level,
                )
            except Exception:
                logger.warning("LLM response failed; using fallback")

        return self._fallback_response(intent_result, faq_result, escalation_level)

    def _fallback_response(
        self,
        intent_result: dict[str, Any],
        faq_result: dict[str, Any],
        escalation_level: int,
    ) -> str:
        intent = intent_result.get("intent", "general_inquiry")
        faq_type = faq_result.get("match_type", "no_match")

        if faq_type == "suggestion":
            faq = faq_result.get("faq")
            if faq:
                return (
                    f"Did you mean to ask about: {faq['question']}? "
                    "I can help with that or connect you to a human agent."
                )

        templates: dict[str, str] = {
            "refund": (
                "I see you're asking about a refund. I've noted this and escalated "
                "it to our billing team who will follow up within 24 hours."
            ),
            "cancel_subscription": (
                "I understand you'd like to cancel your subscription. "
                "I've escalated this to our team who can process the cancellation for you."
            ),
            "billing": (
                "I've noted your billing inquiry. Let me check that for you "
                "or connect you with our billing team."
            ),
            "technical_issue": (
                "I'm sorry you're experiencing a technical issue. "
                "Let me help you troubleshoot or escalate to our engineering team."
            ),
            "account_help": (
                "I can help with account-related questions. "
                "Let me look into that for you."
            ),
            "feature_request": (
                "Thanks for the suggestion! I've shared this with our product team."
            ),
            "greeting": "Hello! How can I help you today?",
            "farewell": "Thanks for reaching out. Have a great day!",
        }

        msg = templates.get(
            intent,
            "Thank you for your message. I'll look into this and get back to you.",
        )
        if escalation_level >= 2:
            msg += " I've created a support ticket and someone will follow up."
        return msg
