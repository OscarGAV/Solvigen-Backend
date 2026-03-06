from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from incident.domain.model.aggregates.Incident import Incident
from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentStatus,
    Priority,
    Category,
    IncidentType,
)


_OPEN_STATUSES = (
    IncidentStatus.OPEN,
    IncidentStatus.IN_PROGRESS,
    IncidentStatus.ESCALATED,
    IncidentStatus.PENDING,
)


class IncidentRepositoryImpl:
    """
    Concrete implementation of IncidentRepository.
    All persistence operations for the Incident aggregate.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, incident: Incident) -> Incident:
        self._session.add(incident)
        await self._session.commit()
        await self._session.refresh(incident)
        return incident

    async def find_by_id(self, incident_id: int) -> Incident | None:
        result = await self._session.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

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
        stmt = select(Incident)

        filters = []
        if status is not None:
            filters.append(Incident.status == status)
        if priority is not None:
            filters.append(Incident.priority == priority)
        if category is not None:
            filters.append(Incident.category == category)
        if incident_type is not None:
            filters.append(Incident.incident_type == incident_type)
        if reporter_id is not None:
            filters.append(Incident.reporter_id == reporter_id)
        if assigned_to_id is not None:
            filters.append(Incident.assigned_to_id == assigned_to_id)
        if is_recurring is not None:
            filters.append(Incident.is_recurring == is_recurring)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_reporter(self, reporter_id: int) -> list[Incident]:
        result = await self._session.execute(
            select(Incident)
            .where(Incident.reporter_id == reporter_id)
            .order_by(Incident.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_open(self) -> list[Incident]:
        result = await self._session.execute(
            select(Incident)
            .where(Incident.status.in_(_OPEN_STATUSES))
            .order_by(Incident.created_at.asc())  # oldest first = highest urgency
        )
        return list(result.scalars().all())

    async def find_recurring(self, min_count: int = 2) -> list[Incident]:
        result = await self._session.execute(
            select(Incident)
            .where(
                and_(
                    Incident.is_recurring == True,  # noqa: E712
                    Incident.recurrence_count >= min_count,
                )
            )
            .order_by(Incident.recurrence_count.desc())
        )
        return list(result.scalars().all())

    async def find_by_category_and_description_similarity(
        self,
        category: Category | None,
        keywords: list[str],
        limit: int = 10,
    ) -> list[Incident]:
        """
        Basic keyword similarity search using ILIKE on description.
        For production, replace with pgvector or full-text search.
        """
        stmt = select(Incident)

        conditions = []
        if category is not None:
            conditions.append(Incident.category == category)

        if keywords:
            keyword_conditions = [
                or_(
                    Incident.title.ilike(f"%{kw}%"),
                    Incident.description.ilike(f"%{kw}%"),
                )
                for kw in keywords
            ]
            conditions.append(or_(*keyword_conditions))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt
            .where(Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
            .order_by(Incident.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(
            select(Incident.status, func.count(Incident.id))
            .group_by(Incident.status)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def count_by_priority(self) -> dict[str, int]:
        result = await self._session.execute(
            select(Incident.priority, func.count(Incident.id))
            .group_by(Incident.priority)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def count_by_category(self) -> dict[str, int]:
        result = await self._session.execute(
            select(Incident.category, func.count(Incident.id))
            .group_by(Incident.category)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def delete(self, incident: Incident) -> None:
        await self._session.delete(incident)
        await self._session.commit()
