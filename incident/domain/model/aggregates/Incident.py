from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, Integer, Float, Enum as SAEnum, JSON
from shared.infrastructure.persistence.configuration.database_configuration import Base

from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentType,
    Category,
    Priority,
    IncidentStatus,
    SLA_HOURS,
)
from incident.domain.model.valueobjects.AIAnalysis import AIAnalysis


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    """
    Aggregate Root: Incident
    Manages the complete lifecycle of an IT support ticket.
    Domain logic lives here; orchestration lives in CommandService.
    """
    __tablename__ = "incidents"

    # =========================================================================
    # IDENTITY & AUDIT
    # =========================================================================
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # =========================================================================
    # USER INPUT (raw)
    # =========================================================================
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Reporter info
    reporter_id: Mapped[int] = mapped_column(nullable=False)          # FK → users.id
    reporter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    assigned_to_id: Mapped[int | None] = mapped_column(nullable=True) # FK → users.id

    # =========================================================================
    # CLASSIFICATION (Value Objects stored as DB enums/strings)
    # =========================================================================
    incident_type: Mapped[IncidentType] = mapped_column(
        SAEnum(IncidentType), nullable=False, default=IncidentType.INCIDENT
    )
    category: Mapped[Category] = mapped_column(
        SAEnum(Category), nullable=False, default=Category.OTHER
    )
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority), nullable=False, default=Priority.MEDIUM
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN
    )

    # =========================================================================
    # AI ANALYSIS (flattened from AIAnalysis value object)
    # =========================================================================
    ai_classification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggested_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    ai_priority_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Analytical agent
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    root_cause_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    preventive_actions: Mapped[list] = mapped_column(JSON, default=list)

    # Escalation
    escalation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalated_by_role: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # =========================================================================
    # DOMAIN LOGIC — Lifecycle Transitions
    # =========================================================================

    def start_progress(self, agent_id: int) -> None:
        """Assign and begin working on the incident."""
        if self.status not in (IncidentStatus.OPEN, IncidentStatus.PENDING):
            raise ValueError(
                f"Cannot start progress on incident in status '{self.status}'"
            )
        self.assigned_to_id = agent_id
        self.status = IncidentStatus.IN_PROGRESS
        self.updated_at = utc_now()

    def escalate(self, notes: str, summary: str, escalated_by_role: str | None = None) -> None:
        """Escalate incident to a higher support tier."""
        if self.status == IncidentStatus.RESOLVED:
            raise ValueError("Cannot escalate a resolved incident")
        if self.status == IncidentStatus.CLOSED:
            raise ValueError("Cannot escalate a closed incident")

        self.escalation_notes = notes
        self.escalation_summary = summary
        self.escalated_by_role = escalated_by_role
        self.status = IncidentStatus.ESCALATED
        self.updated_at = utc_now()

    def put_on_pending(self) -> None:
        """Mark as pending external action."""
        if self.status not in (IncidentStatus.IN_PROGRESS, IncidentStatus.ESCALATED):
            raise ValueError(
                f"Cannot set pending from status '{self.status}'"
            )
        self.status = IncidentStatus.PENDING
        self.updated_at = utc_now()

    def resolve(self) -> None:
        """Mark the incident as resolved."""
        if self.status == IncidentStatus.CLOSED:
            raise ValueError("Incident is already closed")
        if self.status == IncidentStatus.RESOLVED:
            raise ValueError("Incident is already resolved")

        self.status = IncidentStatus.RESOLVED
        self.resolved_at = utc_now()
        self.updated_at = utc_now()

    def close(self) -> None:
        """Close a resolved incident after confirmation."""
        if self.status != IncidentStatus.RESOLVED:
            raise ValueError("Only resolved incidents can be closed")

        self.status = IncidentStatus.CLOSED
        self.updated_at = utc_now()

    def reopen(self) -> None:
        """Reopen a resolved/closed incident."""
        if self.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            raise ValueError("Only resolved or closed incidents can be reopened")

        self.status = IncidentStatus.OPEN
        self.resolved_at = None
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC — AI Analysis
    # =========================================================================

    def apply_ai_analysis(self, analysis: AIAnalysis) -> None:
        """
        Apply the structured output from the GenIA agent pipeline.
        Overwrites any previous AI analysis.
        """
        self.incident_type = analysis.incident_type
        self.category = analysis.category
        self.priority = analysis.priority

        self.ai_classification_reason = analysis.classification_reason
        self.ai_priority_reason = analysis.priority_reason
        self.ai_suggested_response = analysis.suggested_response
        self.ai_classification_confidence = analysis.classification_confidence
        self.ai_priority_confidence = analysis.priority_confidence

        self.is_recurring = analysis.is_recurring
        self.recurrence_count = analysis.recurrence_count
        self.root_cause_hypothesis = analysis.root_cause_hypothesis
        self.preventive_actions = analysis.preventive_actions

        self.updated_at = utc_now()

    # =========================================================================
    # BUSINESS RULES
    # =========================================================================

    def is_sla_breached(self) -> bool:
        if self.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            return False
        sla_hours = SLA_HOURS[self.priority]
        created = self.created_at.replace(tzinfo=timezone.utc) if self.created_at.tzinfo is None else self.created_at
        elapsed = (utc_now() - created).total_seconds() / 3600
        return elapsed > sla_hours

    def sla_remaining_hours(self) -> float:
        sla_hours = SLA_HOURS[self.priority]
        created = self.created_at.replace(tzinfo=timezone.utc) if self.created_at.tzinfo is None else self.created_at
        elapsed = (utc_now() - created).total_seconds() / 3600
        return round(sla_hours - elapsed, 2)

    def can_be_assigned(self) -> bool:
        return self.status in (IncidentStatus.OPEN, IncidentStatus.PENDING)

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "raw_input": self.raw_input,
            "reporter_id": self.reporter_id,
            "reporter_name": self.reporter_name,
            "assigned_to_id": self.assigned_to_id,
            "incident_type": self.incident_type,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "ai_classification_reason": self.ai_classification_reason,
            "ai_priority_reason": self.ai_priority_reason,
            "ai_suggested_response": self.ai_suggested_response,
            "ai_classification_confidence": self.ai_classification_confidence,
            "ai_priority_confidence": self.ai_priority_confidence,
            "is_recurring": self.is_recurring,
            "recurrence_count": self.recurrence_count,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "preventive_actions": self.preventive_actions,
            "is_sla_breached": self.is_sla_breached(),
            "sla_remaining_hours": self.sla_remaining_hours(),
            "escalation_notes": self.escalation_notes,
            "escalation_summary": self.escalation_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
