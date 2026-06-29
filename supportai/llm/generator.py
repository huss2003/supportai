import re
from typing import Any

from supportai.llm.llm_client import LLMClient
from supportai.llm.prompts import GENERATION_FALLBACK_PROMPT, GENERATION_SYSTEM_PROMPT
from supportai.llm.templates import TemplateMatrix

_HALLUCATION_PATTERNS = [
    re.compile(r"\b(?:order|transaction|account)\s*#?\s*\d{5,}\b", re.IGNORECASE),
    re.compile(r"\b(?:REF|ORD|TXN)[-_]?\d{4,}\b", re.IGNORECASE),
    re.compile(r"\$\d{3,}\.\d{2}\b"),
    re.compile(r"\b(?:email|phone)\s*:?\s*[\w.@+-]+@[\w-]+\.[\w.]+", re.IGNORECASE),
]


class ResponseGenerator:
    def __init__(
        self,
        llm_client: LLMClient,
        template_matrix: TemplateMatrix | None = None,
    ) -> None:
        self._llm = llm_client
        self._templates = template_matrix or TemplateMatrix()

    async def generate(
        self,
        message: str,
        intent: str = "general",
        sentiment: str = "neutral",
        escalation: str = "none",
        context: str = "",
        agent_name: str = "Agent",
        company_name: str = "Support",
        max_chars: int = 1000,
    ) -> dict[str, Any]:
        llm_response = await self._try_llm(
            message=message,
            intent=intent,
            sentiment=sentiment,
            escalation=escalation,
            context=context,
            agent_name=agent_name,
            company_name=company_name,
            max_chars=max_chars,
        )

        if llm_response and self._validate_response(llm_response, max_chars):
            return {
                "response": llm_response,
                "source": "llm",
                "template_id": None,
            }

        template_text, template_id = self._template_response(
            intent=intent,
            sentiment=sentiment,
            escalation=escalation,
        )
        return {
            "response": template_text,
            "source": "template",
            "template_id": template_id,
        }

    async def _try_llm(
        self,
        message: str,
        intent: str,
        sentiment: str,
        escalation: str,
        context: str,
        agent_name: str,
        company_name: str,
        max_chars: int,
    ) -> str | None:
        system_prompt = GENERATION_SYSTEM_PROMPT.format(
            company_name=company_name,
            max_chars=max_chars,
            agent_name=agent_name,
            intent=intent,
            sentiment=sentiment,
            escalation=escalation,
            context=context,
        )
        try:
            response = await self._llm.generate_response(
                system_prompt=system_prompt,
                message=message,
                temperature=0.3,
            )
            if response.strip():
                return response.strip()
        except RuntimeError:
            pass

        try:
            fallback = GENERATION_FALLBACK_PROMPT.format(
                company_name=company_name,
                max_chars=max_chars,
                agent_name=agent_name,
                intent=intent,
                sentiment=sentiment,
            )
            response = await self._llm.generate_response(
                system_prompt=fallback,
                message=message,
                temperature=0.3,
            )
            if response.strip():
                return response.strip()
        except RuntimeError:
            pass

        return None

    def _validate_response(self, response: str, max_chars: int = 1000) -> bool:
        if not response or len(response) > max_chars:
            return False
        for pattern in _HALLUCATION_PATTERNS:
            if pattern.search(response):
                return False
        return True

    def _template_response(
        self,
        intent: str,
        sentiment: str,
        escalation: str,
    ) -> tuple[str, str | None]:
        template_id = self._templates.get_template_id(
            intent=intent,
            sentiment=sentiment,
            escalation=escalation,
        )
        text = self._templates.get(
            intent=intent,
            sentiment=sentiment,
            escalation=escalation,
        )
        return text, template_id
