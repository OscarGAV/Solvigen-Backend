import logging
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from incident.application.internal.commandservice.CommandServiceImpl import IncidentCommandServiceImpl
from incident.application.internal.queryservice.QueryServiceImpl import IncidentQueryServiceImpl
from incident.application.internal.agentservice.AgentOrchestrator import AgentOrchestrator
from incident.infrastructure.persistence.repositories.IncidentRepositoryImpl import IncidentRepositoryImpl
from incident.interface.api.rest.assemblers.IncidentResourceAssembler import IncidentResourceAssembler
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
from iam.infrastructure.tokenservice.jwt.BearerTokenService import get_current_active_user
from iam.domain.model.aggregates.User import User
from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


# =============================================================================
# DEPENDENCY FACTORIES
# =============================================================================

def _get_anthropic_client() -> AsyncAnthropic:
    """Instantiate the Anthropic async client (API key read from env)."""
    return AsyncAnthropic()


def _build_command_service(
    db: AsyncSession,
    client: AsyncAnthropic,
) -> IncidentCommandServiceImpl:
    repository = IncidentRepositoryImpl(db)
    orchestrator = AgentOrchestrator(client)
    return IncidentCommandServiceImpl(repository, orchestrator)


def _build_query_service(db: AsyncSession) -> IncidentQueryServiceImpl:
    repository = IncidentRepositoryImpl(db)
    return IncidentQueryServiceImpl(repository)


# =============================================================================
# COMMANDS — Write operations
# =============================================================================

@router.post(
    "",
    response_model=IncidentResponse,
    status_code=201,
    summary="Create incident",
    description=(
        "Submit a ticket in natural language. "
        "The GenIA pipeline will classify, prioritize and generate a suggested response automatically."
    ),
    responses={
        201: {"description": "Incident created and analyzed by GenIA agents"},
        400: {"description": "Invalid or empty input"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error or GenIA pipeline failure"},
    },
)
async def create_incident(
    request: CreateIncidentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    """
    Create a new incident.

    - **raw_input**: Free-text description (informal, incomplete or ambiguous text is accepted)

    The system will automatically:
    - Classify the ticket type and technical category
    - Assign a business priority based on impact and urgency
    - Generate a suggested response for the end user
    - Detect if this is a recurring incident and propose corrective actions
    """
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_create_command(
            request=request,
            reporter_id=current_user.id,
            reporter_name=current_user.full_name or current_user.username,
        )
        incident = await service.create_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating incident: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/start",
    response_model=IncidentResponse,
    summary="Start working on incident",
    responses={
        200: {"description": "Incident assigned and set to in-progress"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Authentication required"},
        404: {"description": "Incident not found"},
    },
)
async def start_progress(
    request: StartProgressRequest,
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    """Assign the incident to an agent and begin working on it."""
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_start_progress_command(incident_id, request)
        incident = await service.start_progress(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error("Error starting progress on incident %s: %s", incident_id, e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/escalate",
    response_model=IncidentResponse,
    summary="Escalate incident",
    description="Escalate to a higher support tier. GenIA auto-generates an escalation summary.",
    responses={
        200: {"description": "Incident escalated with AI-generated summary"},
        400: {"description": "Invalid escalation (e.g. already resolved)"},
        401: {"description": "Authentication required"},
        404: {"description": "Incident not found"},
    },
)
async def escalate_incident(
    request: EscalateIncidentRequest,
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    """Escalate an incident. The AI will generate a structured escalation summary for the L2 team."""
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_escalate_command(incident_id, current_user.id, current_user.role.value, request)
        incident = await service.escalate_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error("Error escalating incident %s: %s", incident_id, e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/pending",
    response_model=IncidentResponse,
    summary="Set incident to pending",
)
async def put_on_pending(
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_pending_command(incident_id)
        incident = await service.put_on_pending(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/resolve",
    response_model=IncidentResponse,
    summary="Resolve incident",
)
async def resolve_incident(
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_resolve_command(incident_id, current_user.id)
        incident = await service.resolve_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/close",
    response_model=IncidentResponse,
    summary="Close incident",
)
async def close_incident(
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_close_command(incident_id, current_user.id)
        incident = await service.close_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/{incident_id}/reopen",
    response_model=IncidentResponse,
    summary="Reopen incident",
)
async def reopen_incident(
    request: ReopenIncidentRequest,
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_reopen_command(incident_id, current_user.id, request)
        incident = await service.reopen_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/{incident_id}/reanalyze",
    response_model=IncidentResponse,
    summary="Re-run GenIA analysis",
    description="Trigger the full 4-agent pipeline again on an existing incident, optionally with additional context.",
)
async def reanalyze_incident(
    request: ReanalyzeIncidentRequest,
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    client: AsyncAnthropic = Depends(_get_anthropic_client),
):
    try:
        service = _build_command_service(db, client)
        command = IncidentResourceAssembler.to_reanalyze_command(incident_id, request)
        incident = await service.reanalyze_incident(command)
        return IncidentResourceAssembler.to_incident_response(incident)

    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error("Error reanalyzing incident %s: %s", incident_id, e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# QUERIES — Read operations
# =============================================================================

@router.get(
    "",
    response_model=IncidentListResponse,
    summary="List incidents",
    description="Get incidents with optional filters. Supports pagination.",
)
async def list_incidents(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    incident_type: str | None = Query(None),
    reporter_id: int | None = Query(None),
    assigned_to_id: int | None = Query(None),
    is_recurring: bool | None = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        filters = IncidentFilterRequest(
            status=status,
            priority=priority,
            category=category,
            incident_type=incident_type,
            reporter_id=reporter_id,
            assigned_to_id=assigned_to_id,
            is_recurring=is_recurring,
            limit=limit,
            offset=offset,
        )
        service = _build_query_service(db)
        query = IncidentResourceAssembler.to_get_all_query(filters)
        incidents = await service.get_all(query)
        return IncidentResourceAssembler.to_incident_list_response(incidents, limit, offset)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/open",
    response_model=list[IncidentResponse],
    summary="Get all open incidents",
)
async def get_open_incidents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    incidents = await service.get_open(IncidentResourceAssembler.to_get_open_query())
    return [IncidentResourceAssembler.to_incident_response(i) for i in incidents]


@router.get(
    "/recurring",
    response_model=list[IncidentResponse],
    summary="Get recurring incidents",
    description="Incidents flagged by the Analytical Agent as recurring patterns.",
)
async def get_recurring_incidents(
    min_count: int = Query(default=2, ge=2),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    query = IncidentResourceAssembler.to_get_recurring_query(min_count)
    incidents = await service.get_recurring(query)
    return [IncidentResourceAssembler.to_incident_response(i) for i in incidents]


@router.get(
    "/sla-breached",
    response_model=list[IncidentResponse],
    summary="Get SLA-breached incidents",
    description="Open incidents that have exceeded their SLA resolution window.",
)
async def get_sla_breached_incidents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    query = IncidentResourceAssembler.to_get_sla_breached_query()
    incidents = await service.get_sla_breached(query)
    return [IncidentResourceAssembler.to_incident_response(i) for i in incidents]


@router.get(
    "/analytics/summary",
    response_model=PatternSummaryResponse,
    summary="Analytics dashboard summary",
    description="Aggregated incident counts by status, priority and category.",
)
async def get_pattern_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    query = IncidentResourceAssembler.to_get_pattern_summary_query()
    summary = await service.get_pattern_summary(query)
    return IncidentResourceAssembler.to_pattern_summary_response(summary)


@router.get(
    "/my",
    response_model=list[IncidentResponse],
    summary="Get my incidents",
    description="Get all incidents reported by the current authenticated user.",
)
async def get_my_incidents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    query = IncidentResourceAssembler.to_get_by_reporter_query(current_user.id)
    incidents = await service.get_by_reporter(query)
    return [IncidentResourceAssembler.to_incident_response(i) for i in incidents]


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident by ID",
    responses={
        200: {"description": "Incident found"},
        401: {"description": "Authentication required"},
        404: {"description": "Incident not found"},
    },
)
async def get_incident(
    incident_id: int = Path(..., ge=1, description="Incident ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = _build_query_service(db)
    query = IncidentResourceAssembler.to_get_by_id_query(incident_id)
    incident = await service.get_by_id(query)

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return IncidentResourceAssembler.to_incident_response(incident)