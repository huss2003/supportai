TEMPLATES: list[dict[str, str]] = [
    {
        "id": "T01",
        "intent": "refund",
        "sentiment": "frustrated",
        "escalation": "high",
        "text": "I understand this refund delay is frustrating. Let me escalate this to our billing team right away so they can prioritise your case.",
    },
    {
        "id": "T02",
        "intent": "refund",
        "sentiment": "negative",
        "escalation": "medium",
        "text": "I am sorry for the trouble. Let me start a refund review for you. You will hear back within 2-3 business days.",
    },
    {
        "id": "T03",
        "intent": "refund",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "I can help with that refund request. Let me look up your transaction details to get this started.",
    },
    {
        "id": "T04",
        "intent": "cancellation",
        "sentiment": "frustrated",
        "escalation": "high",
        "text": "I understand you want to cancel. I can process that right now. Let me also check if there is anything we can do to make this right.",
    },
    {
        "id": "T05",
        "intent": "cancellation",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "I can process your cancellation request. Before I do, would you mind sharing what led to your decision so we can improve?",
    },
    {
        "id": "T06",
        "intent": "account_access",
        "sentiment": "frustrated",
        "escalation": "medium",
        "text": "I am sorry you are having trouble accessing your account. Let me verify your identity and help you regain access.",
    },
    {
        "id": "T07",
        "intent": "account_access",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "I can help with account access. Please share the email address associated with your account so I can assist.",
    },
    {
        "id": "T08",
        "intent": "billing",
        "sentiment": "negative",
        "escalation": "medium",
        "text": "I apologise for the confusion on your bill. Let me review the charges and explain them clearly.",
    },
    {
        "id": "T09",
        "intent": "billing",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "I would be happy to help with your billing question. Could you share the relevant invoice or transaction ID?",
    },
    {
        "id": "T10",
        "intent": "technical",
        "sentiment": "frustrated",
        "escalation": "high",
        "text": "I am sorry this technical issue is blocking your work. Let me log this with our engineering team and get you a fix as soon as possible.",
    },
    {
        "id": "T11",
        "intent": "technical",
        "sentiment": "negative",
        "escalation": "medium",
        "text": "I understand how disruptive this bug must be. Let me gather some details and escalate this to our technical team.",
    },
    {
        "id": "T12",
        "intent": "technical",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "I can help troubleshoot that. Could you share the steps you took before the issue appeared and any error messages you saw?",
    },
    {
        "id": "T13",
        "intent": "feature_request",
        "sentiment": "positive",
        "escalation": "none",
        "text": "Thank you for the suggestion. I have shared it with our product team for consideration in a future release.",
    },
    {
        "id": "T14",
        "intent": "feature_request",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "That is a great idea. I have passed your feature request along to our product team. They review all suggestions regularly.",
    },
    {
        "id": "T15",
        "intent": "complaint",
        "sentiment": "angry",
        "escalation": "high",
        "text": "I sincerely apologise for your experience. This is not the standard we aim for. I am escalating this to management right now.",
    },
    {
        "id": "T16",
        "intent": "complaint",
        "sentiment": "frustrated",
        "escalation": "medium",
        "text": "I hear your frustration and I am sorry. Let me look into what happened and get back to you with a proper resolution.",
    },
    {
        "id": "T17",
        "intent": "greeting",
        "sentiment": "positive",
        "escalation": "none",
        "text": "Hello and welcome. How can I help you today?",
    },
    {
        "id": "T18",
        "intent": "greeting",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "Hi there. Thanks for reaching out. What can I assist you with?",
    },
    {
        "id": "T19",
        "intent": "farewell",
        "sentiment": "positive",
        "escalation": "none",
        "text": "Glad I could help. If anything else comes up, do not hesitate to reach out. Have a great day.",
    },
    {
        "id": "T20",
        "intent": "general",
        "sentiment": "neutral",
        "escalation": "none",
        "text": "Thank you for contacting us. I will do my best to help. Could you provide a bit more detail about your question?",
    },
]

FALLBACK_TEMPLATE = "Thank you for reaching out. Our team will review your inquiry and get back to you shortly."


class TemplateMatrix:
    def __init__(self) -> None:
        self._templates = TEMPLATES
        self._fallback = FALLBACK_TEMPLATE

    def get(
        self,
        intent: str = "general",
        sentiment: str = "neutral",
        escalation: str = "none",
    ) -> str:
        exact = self._match(intent=intent, sentiment=sentiment, escalation=escalation)
        if exact:
            return exact

        intent_matched = self._match(
            intent=intent, sentiment=sentiment, escalation="none"
        )
        if intent_matched:
            return intent_matched

        intent_sentiment_match = self._match(
            intent=intent, sentiment=sentiment, escalation=None
        )
        if intent_sentiment_match:
            return intent_sentiment_match

        intent_match = self._match(intent=intent, sentiment=None, escalation=None)
        if intent_match:
            return intent_match

        general_match = self._match(intent="general", sentiment=None, escalation=None)
        if general_match:
            return general_match

        return self._fallback

    def get_template_id(
        self,
        intent: str = "general",
        sentiment: str = "neutral",
        escalation: str = "none",
    ) -> str | None:
        for t in self._templates:
            if (
                t["intent"] == intent
                and t["sentiment"] == sentiment
                and t["escalation"] == escalation
            ):
                return t["id"]
        return None

    def _match(
        self,
        intent: str | None = None,
        sentiment: str | None = None,
        escalation: str | None = None,
    ) -> str | None:
        for t in self._templates:
            if intent is not None and t["intent"] != intent:
                continue
            if sentiment is not None and t["sentiment"] != sentiment:
                continue
            if escalation is not None and t["escalation"] != escalation:
                continue
            return t["text"]
        return None
