import json
import logging
from anthropic import AsyncAnthropic

from incident.domain.model.valueobjects.AIAnalysis import AIAnalysis
from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentType,
    Category,
    Priority,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent Prompts
# ---------------------------------------------------------------------------

_CLASSIFIER_SYSTEM = """
You are the Classifier Agent in an IT Service Management (ITSM) system.
Your job is to analyze raw ticket text submitted by users and extract structured data.

Respond ONLY with a valid JSON object. No explanation, no markdown.

Output schema:
{
  "incident_type": "incident" | "request" | "problem",
  "category": "network" | "software" | "hardware" | "access" | "email" | "database" | "security" | "other",
  "title": "<concise title max 80 chars>",
  "description": "<clean structured description>",
  "classification_reason": "<explain your classification in 1-2 sentences>",
  "confidence": <float 0.0-1.0>
}

Definitions:
- incident: unexpected disruption or degradation of a service
- request: formal request for something new (access, software, info)
- problem: underlying root cause of one or more incidents
"""

_PRIORITIZATION_SYSTEM = """
You are the Prioritization Agent in an IT Service Management (ITSM) system.
Given a classified incident, assess its business priority.

Priority levels:
- critical: full service down, massive user impact, revenue/security at risk → SLA 1h
- high: major degradation, many users affected, no workaround → SLA 4h
- medium: partial impact, workaround available, limited users affected → SLA 8h
- low: minor issue, cosmetic, single user, workaround available → SLA 72h

Respond ONLY with a valid JSON object. No explanation, no markdown.

Output schema:
{
  "priority": "critical" | "high" | "medium" | "low",
  "priority_reason": "<explain urgency and impact in 1-2 sentences>",
  "confidence": <float 0.0-1.0>
}
"""

_SUPPORT_SYSTEM = """
You are the Support Agent in an IT Service Management (ITSM) system.
Your job is to draft a clear, empathetic, professional response for the end user.

The response should:
- Acknowledge the issue
- Confirm it has been received and classified
- Give realistic expectations based on priority
- Suggest any immediate workaround if applicable
- Be written in the same language as the original ticket

Respond ONLY with a valid JSON object. No explanation, no markdown.

Output schema:
{
  "suggested_response": "<full response text to send to the user>"
}
"""

_ANALYTICAL_SYSTEM = """
You are the Analytical Agent in an IT Service Management (ITSM) system.
You receive a new incident AND a list of similar past incidents.

Your job:
1. Detect if this incident is recurring (same root cause or pattern)
2. If recurring, identify the most likely root cause
3. Propose preventive or corrective actions

Respond ONLY with a valid JSON object. No explanation, no markdown.

Output schema:
{
  "is_recurring": true | false,
  "recurrence_count": <int, total similar incidents including this one>,
  "root_cause_hypothesis": "<hypothesis or null if not recurring>",
  "preventive_actions": ["<action 1>", "<action 2>"]
}
"""


class AgentOrchestrator:
    """
    Application Service: Orchestrates the 4 GenIA agents sequentially.

    Pipeline:
        raw_input
          → ClassifierAgent   → structured classification
          → PrioritizationAgent → priority + rationale
          → SupportAgent       → user-facing response
          → AnalyticalAgent    → recurrence + root cause
          → AIAnalysis (Value Object)
    """

    def __init__(self, anthropic_client: AsyncAnthropic):
        self._client = anthropic_client
        self._model = "claude-sonnet-4-20250514"

    # =========================================================================
    # PUBLIC — Main entry point
    # =========================================================================

    async def analyze(
        self,
        raw_input: str,
        similar_incidents: list[dict],
    ) -> AIAnalysis:
        """
        Run the full 4-agent pipeline and return a complete AIAnalysis.

        Args:
            raw_input: The original user-submitted ticket text.
            similar_incidents: List of past incident dicts (from Analytical lookup).
        """
        logger.info("Agent pipeline started")

        classification = await self._run_classifier(raw_input)
        logger.info("Classifier done: %s / %s", classification["incident_type"], classification["category"])

        prioritization = await self._run_prioritization(raw_input, classification)
        logger.info("Prioritization done: %s", prioritization["priority"])

        support = await self._run_support(raw_input, classification, prioritization)
        logger.info("Support agent done")

        analytical = await self._run_analytical(raw_input, classification, similar_incidents)
        logger.info("Analytical agent done: recurring=%s", analytical["is_recurring"])

        return AIAnalysis(
            incident_type=IncidentType(classification["incident_type"]),
            category=Category(classification["category"]),
            priority=Priority(prioritization["priority"]),
            classification_reason=classification["classification_reason"],
            priority_reason=prioritization["priority_reason"],
            suggested_response=support["suggested_response"],
            classification_confidence=float(classification.get("confidence", 0.8)),
            priority_confidence=float(prioritization.get("confidence", 0.8)),
            is_recurring=bool(analytical["is_recurring"]),
            recurrence_count=int(analytical.get("recurrence_count", 0)),
            root_cause_hypothesis=analytical.get("root_cause_hypothesis"),
            preventive_actions=analytical.get("preventive_actions", []),
        )

    # =========================================================================
    # PRIVATE — Individual agents
    # =========================================================================

    async def _run_classifier(self, raw_input: str) -> dict:
        """Agente Clasificador: type, category, clean title/description."""
        prompt = f"Classify this IT ticket:\n\n{raw_input}"
        return await self._call_agent(_CLASSIFIER_SYSTEM, prompt)

    async def _run_prioritization(self, raw_input: str, classification: dict) -> dict:
        """Agente Priorizacion: priority based on impact and urgency."""
        prompt = (
            f"Ticket text:\n{raw_input}\n\n"
            f"Classification:\n"
            f"- Type: {classification['incident_type']}\n"
            f"- Category: {classification['category']}\n"
            f"- Title: {classification['title']}\n"
            f"- Description: {classification['description']}\n\n"
            f"Assign the appropriate priority."
        )
        return await self._call_agent(_PRIORITIZATION_SYSTEM, prompt)

    async def _run_support(
        self,
        raw_input: str,
        classification: dict,
        prioritization: dict,
    ) -> dict:
        """Agente Soporte: draft response for the end user."""
        prompt = (
            f"Original ticket:\n{raw_input}\n\n"
            f"Classified as: {classification['incident_type']} / {classification['category']}\n"
            f"Priority: {prioritization['priority']}\n"
            f"Priority reason: {prioritization['priority_reason']}\n\n"
            f"Write a response to send to the user."
        )
        return await self._call_agent(_SUPPORT_SYSTEM, prompt)

    async def _run_analytical(
        self,
        raw_input: str,
        classification: dict,
        similar_incidents: list[dict],
    ) -> dict:
        """Agente Analitico: recurrence detection and root cause analysis."""
        similar_text = (
            json.dumps(similar_incidents, ensure_ascii=False, indent=2)
            if similar_incidents
            else "No similar incidents found."
        )
        prompt = (
            f"New incident:\n{raw_input}\n"
            f"Category: {classification['category']}\n\n"
            f"Similar past incidents:\n{similar_text}\n\n"
            f"Analyze for recurrence and root cause."
        )
        return await self._call_agent(_ANALYTICAL_SYSTEM, prompt)

    async def _call_agent(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Generic method to call the Anthropic API for a single agent.
        Expects the model to return a JSON string.
        """
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if model adds them
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        return json.loads(raw_text)
