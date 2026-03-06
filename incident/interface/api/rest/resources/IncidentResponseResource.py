from datetime import datetime
from pydantic import BaseModel, Field

from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentType,
    Category,
    Priority,
    IncidentStatus,
)


# =============================================================================
# INCIDENT RESPONSES
# =============================================================================

class AIAnalysisResponse(BaseModel):
    """DTO for the AI analysis block within an incident response"""
    incident_type: IncidentType
    category: Category
    priority: Priority
    classification_reason: str
    priority_reason: str
    suggested_response: str
    classification_confidence: float
    priority_confidence: float
    is_recurring: bool
    recurrence_count: int
    root_cause_hypothesis: str | None
    preventive_actions: list[str]

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    """Full incident DTO returned to the client"""
    id: int
    title: str
    description: str
    raw_input: str
    reporter_id: int
    reporter_name: str
    assigned_to_id: int | None

    incident_type: IncidentType
    category: Category
    priority: Priority
    status: IncidentStatus

    # AI fields
    ai_classification_reason: str | None
    ai_priority_reason: str | None
    ai_suggested_response: str | None
    ai_classification_confidence: float
    ai_priority_confidence: float
    is_recurring: bool
    recurrence_count: int
    root_cause_hypothesis: str | None
    preventive_actions: list[str]

    # SLA
    is_sla_breached: bool
    sla_remaining_hours: float

    # Escalation
    escalation_notes: str | None
    escalation_summary: str | None

    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "title": "VPN not connecting since this morning",
                    "description": "User is unable to connect to corporate VPN.",
                    "raw_input": "i cant connect to vpn since this morning, i need to work from home",
                    "reporter_id": 5,
                    "reporter_name": "Maria García",
                    "assigned_to_id": None,
                    "incident_type": "incident",
                    "category": "network",
                    "priority": "high",
                    "status": "open",
                    "ai_classification_reason": "User reports connectivity failure on VPN, typical incident.",
                    "ai_priority_reason": "Impacts remote work capability, no immediate workaround.",
                    "ai_suggested_response": "Thank you for reaching out...",
                    "ai_classification_confidence": 0.95,
                    "ai_priority_confidence": 0.88,
                    "is_recurring": False,
                    "recurrence_count": 0,
                    "root_cause_hypothesis": None,
                    "preventive_actions": [],
                    "is_sla_breached": False,
                    "sla_remaining_hours": 3.5,
                    "escalation_notes": None,
                    "escalation_summary": None,
                    "created_at": "2025-01-05T10:00:00Z",
                    "updated_at": "2025-01-05T10:00:00Z",
                    "resolved_at": None,
                }
            ]
        },
    }


class IncidentListResponse(BaseModel):
    """Paginated list of incidents"""
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int


class PatternSummaryResponse(BaseModel):
    """Analytics dashboard summary"""
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]
