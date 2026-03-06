from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateIncidentCommand:
    """
    Command: Create a new incident from raw natural language input.
    The GenIA pipeline will classify, prioritize and generate a response.
    """
    raw_input: str          # Original text from the user (can be messy/incomplete)
    reporter_id: int
    reporter_name: str


@dataclass(frozen=True)
class StartProgressCommand:
    """
    Command: Assign an incident to an agent and begin work.
    """
    incident_id: int
    agent_id: int           # User ID of the support agent taking ownership


@dataclass(frozen=True)
class EscalateIncidentCommand:
    """
    Command: Escalate an incident to a higher support tier.
    The GenIA pipeline auto-generates an escalation summary.
    """
    incident_id: int
    escalated_by_id: int
    notes: str              # Manual notes from the escalating agent


@dataclass(frozen=True)
class ResolveIncidentCommand:
    """
    Command: Mark an incident as resolved.
    """
    incident_id: int
    resolved_by_id: int


@dataclass(frozen=True)
class CloseIncidentCommand:
    """
    Command: Close a resolved incident after user confirmation.
    """
    incident_id: int
    closed_by_id: int


@dataclass(frozen=True)
class ReopenIncidentCommand:
    """
    Command: Reopen a resolved or closed incident.
    """
    incident_id: int
    reason: str
    reopened_by_id: int


@dataclass(frozen=True)
class PendingIncidentCommand:
    """
    Command: Put incident on hold, waiting for external action.
    """
    incident_id: int


@dataclass(frozen=True)
class ReanalyzeIncidentCommand:
    """
    Command: Trigger the GenIA pipeline again on an existing incident.
    Useful when the original raw input was updated or enriched.
    """
    incident_id: int
    additional_context: str | None = None
