import logging

from incident.domain.model.aggregates.Incident import Incident
from incident.domain.model.queries.IncidentQueries import (
    GetIncidentByIdQuery,
    GetAllIncidentsQuery,
    GetIncidentsByReporterQuery,
    GetOpenIncidentsQuery,
    GetRecurringIncidentsQuery,
    GetSLABreachedIncidentsQuery,
    GetIncidentPatternSummaryQuery,
)
from incident.domain.repositories.IncidentRepository import IncidentRepository

logger = logging.getLogger(__name__)


class IncidentQueryServiceImpl:
    """
    Query Service for Incident Context.
    Handles all read operations following CQRS pattern.
    """

    def __init__(self, repository: IncidentRepository):
        self._repository = repository

    async def get_by_id(self, query: GetIncidentByIdQuery) -> Incident | None:
        return await self._repository.find_by_id(query.incident_id)

    async def get_all(self, query: GetAllIncidentsQuery) -> list[Incident]:
        return await self._repository.find_all(
            status=query.status,
            priority=query.priority,
            category=query.category,
            incident_type=query.incident_type,
            reporter_id=query.reporter_id,
            assigned_to_id=query.assigned_to_id,
            is_recurring=query.is_recurring,
            limit=query.limit,
            offset=query.offset,
        )

    async def get_by_reporter(self, query: GetIncidentsByReporterQuery) -> list[Incident]:
        return await self._repository.find_by_reporter(query.reporter_id)

    async def get_open(self, query: GetOpenIncidentsQuery) -> list[Incident]:
        return await self._repository.find_open()

    async def get_recurring(self, query: GetRecurringIncidentsQuery) -> list[Incident]:
        return await self._repository.find_recurring(query.min_recurrence_count)

    async def get_sla_breached(self, query: GetSLABreachedIncidentsQuery) -> list[Incident]:
        """Return all open incidents that have exceeded their SLA window."""
        open_incidents = await self._repository.find_open()
        return [i for i in open_incidents if i.is_sla_breached()]

    async def get_pattern_summary(self, query: GetIncidentPatternSummaryQuery) -> dict:
        """
        Aggregate statistics for the analytics dashboard.
        Returns counts by status, priority and category.
        """
        by_status = await self._repository.count_by_status()
        by_priority = await self._repository.count_by_priority()
        by_category = await self._repository.count_by_category()

        return {
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
        }
