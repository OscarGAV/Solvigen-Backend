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
from incident.domain.model.queries.IncidentQueries import (
    GetIncidentByIdQuery,
    GetAllIncidentsQuery,
    GetIncidentsByReporterQuery,
    GetOpenIncidentsQuery,
    GetRecurringIncidentsQuery,
    GetSLABreachedIncidentsQuery,
    GetIncidentPatternSummaryQuery,
)
from incident.interface.api.rest.resources.IncidentRequestResource import (
    CreateIncidentRequest,
    StartProgressRequest,
    EscalateIncidentRequest,
    ReopenIncidentRequest,
    ReanalyzeIncidentRequest,
    IncidentFilterRequest,
)
from incident.interface.api.rest.resources.IncidentResponseResource import (
    IncidentResponse,
    IncidentListResponse,
    PatternSummaryResponse,
)
from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentType,
    Category,
    Priority,
)


class IncidentResourceAssembler:
    """
    Assembler: transforms between presentation and domain layers.
    All methods are static — no state, no instantiation needed.
    """

    # =========================================================================
    # Request → Command
    # =========================================================================

    @staticmethod
    def to_create_command(
        request: CreateIncidentRequest,
        reporter_id: int,
        reporter_name: str,
    ) -> CreateIncidentCommand:
        return CreateIncidentCommand(
            raw_input=request.raw_input,
            reporter_id=reporter_id,
            reporter_name=reporter_name,
        )

    @staticmethod
    def to_start_progress_command(
        incident_id: int,
        request: StartProgressRequest,
    ) -> StartProgressCommand:
        return StartProgressCommand(
            incident_id=incident_id,
            agent_id=request.agent_id,
        )

    @staticmethod
    def to_escalate_command(
        incident_id: int,
        escalated_by_id: int,
        escalated_by_role: str,
        request: EscalateIncidentRequest,
    ) -> EscalateIncidentCommand:
        return EscalateIncidentCommand(
            incident_id=incident_id,
            escalated_by_id=escalated_by_id,
            escalated_by_role=escalated_by_role,
            notes=request.notes,
        )

    @staticmethod
    def to_resolve_command(incident_id: int, resolved_by_id: int) -> ResolveIncidentCommand:
        return ResolveIncidentCommand(
            incident_id=incident_id,
            resolved_by_id=resolved_by_id,
        )

    @staticmethod
    def to_close_command(incident_id: int, closed_by_id: int) -> CloseIncidentCommand:
        return CloseIncidentCommand(
            incident_id=incident_id,
            closed_by_id=closed_by_id,
        )

    @staticmethod
    def to_reopen_command(
        incident_id: int,
        reopened_by_id: int,
        request: ReopenIncidentRequest,
    ) -> ReopenIncidentCommand:
        return ReopenIncidentCommand(
            incident_id=incident_id,
            reason=request.reason,
            reopened_by_id=reopened_by_id,
        )

    @staticmethod
    def to_pending_command(incident_id: int) -> PendingIncidentCommand:
        return PendingIncidentCommand(incident_id=incident_id)

    @staticmethod
    def to_reanalyze_command(
        incident_id: int,
        request: ReanalyzeIncidentRequest,
    ) -> ReanalyzeIncidentCommand:
        return ReanalyzeIncidentCommand(
            incident_id=incident_id,
            additional_context=request.additional_context,
        )

    # =========================================================================
    # Params → Query
    # =========================================================================

    @staticmethod
    def to_get_by_id_query(incident_id: int) -> GetIncidentByIdQuery:
        return GetIncidentByIdQuery(incident_id=incident_id)

    @staticmethod
    def to_get_all_query(filters: IncidentFilterRequest) -> GetAllIncidentsQuery:
        return GetAllIncidentsQuery(
            status=filters.status,
            priority=Priority(filters.priority) if filters.priority else None,
            category=Category(filters.category) if filters.category else None,
            incident_type=IncidentType(filters.incident_type) if filters.incident_type else None,
            reporter_id=filters.reporter_id,
            assigned_to_id=filters.assigned_to_id,
            is_recurring=filters.is_recurring,
            limit=filters.limit,
            offset=filters.offset,
        )

    @staticmethod
    def to_get_by_reporter_query(reporter_id: int) -> GetIncidentsByReporterQuery:
        return GetIncidentsByReporterQuery(reporter_id=reporter_id)

    @staticmethod
    def to_get_open_query() -> GetOpenIncidentsQuery:
        return GetOpenIncidentsQuery()

    @staticmethod
    def to_get_recurring_query(min_count: int = 2) -> GetRecurringIncidentsQuery:
        return GetRecurringIncidentsQuery(min_recurrence_count=min_count)

    @staticmethod
    def to_get_sla_breached_query() -> GetSLABreachedIncidentsQuery:
        return GetSLABreachedIncidentsQuery()

    @staticmethod
    def to_get_pattern_summary_query() -> GetIncidentPatternSummaryQuery:
        return GetIncidentPatternSummaryQuery()

    # =========================================================================
    # Domain → Response
    # =========================================================================

    @staticmethod
    def to_incident_response(incident: Incident) -> IncidentResponse:
        return IncidentResponse(
            id=incident.id,
            title=incident.title,
            description=incident.description,
            raw_input=incident.raw_input,
            reporter_id=incident.reporter_id,
            reporter_name=incident.reporter_name,
            assigned_to_id=incident.assigned_to_id,
            incident_type=incident.incident_type,
            category=incident.category,
            priority=incident.priority,
            status=incident.status,
            ai_classification_reason=incident.ai_classification_reason,
            ai_priority_reason=incident.ai_priority_reason,
            ai_suggested_response=incident.ai_suggested_response,
            ai_classification_confidence=incident.ai_classification_confidence,
            ai_priority_confidence=incident.ai_priority_confidence,
            is_recurring=incident.is_recurring,
            recurrence_count=incident.recurrence_count,
            root_cause_hypothesis=incident.root_cause_hypothesis,
            preventive_actions=incident.preventive_actions or [],
            is_sla_breached=incident.is_sla_breached(),
            sla_remaining_hours=incident.sla_remaining_hours(),
            escalation_notes=incident.escalation_notes,
            escalation_summary=incident.escalation_summary,
            escalated_by_role=incident.escalated_by_role,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            resolved_at=incident.resolved_at,
        )

    @staticmethod
    def to_incident_list_response(
        incidents: list[Incident],
        limit: int,
        offset: int,
    ) -> IncidentListResponse:
        return IncidentListResponse(
            items=[IncidentResourceAssembler.to_incident_response(i) for i in incidents],
            total=len(incidents),
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def to_pattern_summary_response(summary: dict) -> PatternSummaryResponse:
        return PatternSummaryResponse(
            by_status=summary.get("by_status", {}),
            by_priority=summary.get("by_priority", {}),
            by_category=summary.get("by_category", {}),
        )