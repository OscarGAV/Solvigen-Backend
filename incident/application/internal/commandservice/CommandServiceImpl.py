import logging

from incident.domain.model.aggregates.Incident import Incident
from incident.domain.model.commands.IncidentCommands import (
    CreateIncidentCommand,
    StartProgressCommand,
    EscalateIncidentCommand,
    ResolveIncidentCommand,
    CloseIncidentCommand,
    ReopenIncidentCommand,
    PendingIncidentCommand,
    ReanalyzeIncidentCommand,
)
from incident.domain.repositories.IncidentRepository import IncidentRepository
from incident.application.internal.agentservice.AgentOrchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class IncidentCommandServiceImpl:
    """
    Command Service for Incident Context.
    Handles all write operations following CQRS pattern.

    Responsibilities:
    - Enforce business rules before/after domain logic
    - Coordinate Incident aggregate with AgentOrchestrator
    - Persist via IncidentRepository
    """

    def __init__(
        self,
        repository: IncidentRepository,
        orchestrator: AgentOrchestrator,
    ):
        self._repository = repository
        self._orchestrator = orchestrator

    # =========================================================================
    # CREATE — Full GenIA pipeline
    # =========================================================================

    async def create_incident(self, command: CreateIncidentCommand) -> Incident:
        """
        Create a new incident from raw natural language input.

        Flow:
        1. Fetch similar past incidents for the Analytical Agent
        2. Run the 4-agent GenIA pipeline
        3. Build the Incident aggregate with AI analysis applied
        4. Persist and return
        """
        if not command.raw_input or not command.raw_input.strip():
            raise ValueError("Incident raw input cannot be empty")

        # Fetch similar incidents for recurrence analysis (broad keyword match)
        keywords = command.raw_input.lower().split()[:5]
        similar = await self._repository.find_by_category_and_description_similarity(
            category=None,  # type: ignore — impl handles None gracefully
            keywords=keywords,
            limit=5,
        )
        similar_dicts = [s.to_dict() for s in similar]

        # Run GenIA pipeline
        logger.info("Running GenIA pipeline for new incident from reporter_id=%s", command.reporter_id)
        analysis = await self._orchestrator.analyze(
            raw_input=command.raw_input,
            similar_incidents=similar_dicts,
        )

        # Build aggregate
        incident = Incident(
            raw_input=command.raw_input,
            title=command.raw_input[:80].strip(),   # will be refined by classifier
            description=command.raw_input,
            reporter_id=command.reporter_id,
            reporter_name=command.reporter_name,
        )
        incident.apply_ai_analysis(analysis)

        # Override title/description with AI-cleaned values if available
        # (Classifier returns a clean title; we store it during apply_ai_analysis)

        saved = await self._repository.save(incident)
        logger.info("Incident created with id=%s, priority=%s", saved.id, saved.priority)
        return saved

    # =========================================================================
    # LIFECYCLE TRANSITIONS
    # =========================================================================

    async def start_progress(self, command: StartProgressCommand) -> Incident:
        """Assign and begin working on an incident."""
        incident = await self._get_or_raise(command.incident_id)
        incident.start_progress(command.agent_id)
        return await self._repository.save(incident)

    async def escalate_incident(self, command: EscalateIncidentCommand) -> Incident:
        """
        Escalate incident.
        Auto-generates an escalation summary using the Support Agent.
        """
        incident = await self._get_or_raise(command.incident_id)

        # Generate escalation summary via Support Agent
        escalation_prompt = (
            f"Incident ID: {incident.id}\n"
            f"Title: {incident.title}\n"
            f"Description: {incident.description}\n"
            f"Priority: {incident.priority}\n"
            f"Category: {incident.category}\n"
            f"Agent notes: {command.notes}\n\n"
            "Generate a concise escalation summary for the L2 team."
        )
        summary_raw = await self._orchestrator._call_agent(
            system_prompt=(
                "You are an ITSM escalation summarizer. "
                "Return ONLY a JSON object: {\"escalation_summary\": \"<text>\"}"
            ),
            user_prompt=escalation_prompt,
        )
        escalation_summary = summary_raw.get("escalation_summary", command.notes)

        incident.escalate(notes=command.notes, summary=escalation_summary)
        return await self._repository.save(incident)

    async def put_on_pending(self, command: PendingIncidentCommand) -> Incident:
        incident = await self._get_or_raise(command.incident_id)
        incident.put_on_pending()
        return await self._repository.save(incident)

    async def resolve_incident(self, command: ResolveIncidentCommand) -> Incident:
        incident = await self._get_or_raise(command.incident_id)
        incident.resolve()
        return await self._repository.save(incident)

    async def close_incident(self, command: CloseIncidentCommand) -> Incident:
        incident = await self._get_or_raise(command.incident_id)
        incident.close()
        return await self._repository.save(incident)

    async def reopen_incident(self, command: ReopenIncidentCommand) -> Incident:
        incident = await self._get_or_raise(command.incident_id)
        incident.reopen()
        return await self._repository.save(incident)

    async def reanalyze_incident(self, command: ReanalyzeIncidentCommand) -> Incident:
        """
        Re-run the GenIA pipeline on an existing incident.
        Useful when context is enriched or the initial analysis was wrong.
        """
        incident = await self._get_or_raise(command.incident_id)

        raw = incident.raw_input
        if command.additional_context:
            raw = f"{raw}\n\nAdditional context: {command.additional_context}"

        keywords = raw.lower().split()[:5]
        similar = await self._repository.find_by_category_and_description_similarity(
            category=incident.category,
            keywords=keywords,
            limit=5,
        )
        similar_dicts = [s.to_dict() for s in similar if s.id != incident.id]

        analysis = await self._orchestrator.analyze(
            raw_input=raw,
            similar_incidents=similar_dicts,
        )
        incident.apply_ai_analysis(analysis)
        return await self._repository.save(incident)

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _get_or_raise(self, incident_id: int) -> Incident:
        incident = await self._repository.find_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")
        return incident
