from dataclasses import dataclass

from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentStatus,
    Priority,
    Category,
    IncidentType,
)


@dataclass(frozen=True)
class GetIncidentByIdQuery:
    """Query: Get a single incident by its ID"""
    incident_id: int


@dataclass(frozen=True)
class GetAllIncidentsQuery:
    """Query: Get all incidents with optional filters"""
    status: IncidentStatus | None = None
    priority: Priority | None = None
    category: Category | None = None
    incident_type: IncidentType | None = None
    reporter_id: int | None = None
    assigned_to_id: int | None = None
    is_recurring: bool | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetIncidentsByReporterQuery:
    """Query: Get all incidents submitted by a specific user"""
    reporter_id: int


@dataclass(frozen=True)
class GetOpenIncidentsQuery:
    """Query: Get all unresolved incidents (OPEN, IN_PROGRESS, ESCALATED, PENDING)"""
    pass


@dataclass(frozen=True)
class GetRecurringIncidentsQuery:
    """Query: Get incidents flagged as recurring by the Analytical Agent"""
    min_recurrence_count: int = 2


@dataclass(frozen=True)
class GetSLABreachedIncidentsQuery:
    """Query: Get incidents that have exceeded their SLA window"""
    pass


@dataclass(frozen=True)
class GetIncidentPatternSummaryQuery:
    """Query: Get aggregated statistics for the analytics dashboard"""
    pass
