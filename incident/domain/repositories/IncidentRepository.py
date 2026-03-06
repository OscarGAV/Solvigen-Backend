from typing import Protocol

from incident.domain.model.aggregates.Incident import Incident
from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentStatus,
    Priority,
    Category,
    IncidentType,
)


class IncidentRepository(Protocol):
    """
    Repository interface for the Incident aggregate.
    Defined in the domain layer — infrastructure implements it.
    """

    async def save(self, incident: Incident) -> Incident:
        """Persist a new or updated incident"""
        ...

    async def find_by_id(self, incident_id: int) -> Incident | None:
        """Find incident by primary key"""
        ...

    async def find_all(
        self,
        status: IncidentStatus | None = None,
        priority: Priority | None = None,
        category: Category | None = None,
        incident_type: IncidentType | None = None,
        reporter_id: int | None = None,
        assigned_to_id: int | None = None,
        is_recurring: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Incident]:
        """Find all incidents with optional filters"""
        ...

    async def find_by_reporter(self, reporter_id: int) -> list[Incident]:
        """Find all incidents by a specific reporter"""
        ...

    async def find_open(self) -> list[Incident]:
        """Find all non-resolved, non-closed incidents"""
        ...

    async def find_recurring(self, min_count: int = 2) -> list[Incident]:
        """Find incidents flagged as recurring by the Analytical Agent"""
        ...

    async def find_by_category_and_description_similarity(
        self, category: Category, keywords: list[str], limit: int = 10
    ) -> list[Incident]:
        """
        Find similar past incidents by category + keyword matching.
        Used by the Analytical Agent to detect recurrence patterns.
        """
        ...

    async def count_by_category(self) -> dict[str, int]:
        """Aggregate count of incidents per category"""
        ...

    async def count_by_status(self) -> dict[str, int]:
        """Aggregate count of incidents per status"""
        ...

    async def count_by_priority(self) -> dict[str, int]:
        """Aggregate count of incidents per priority"""
        ...

    async def delete(self, incident: Incident) -> None:
        """Delete an incident (admin use only)"""
        ...
