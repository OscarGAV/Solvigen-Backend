from pydantic import BaseModel, Field, field_validator

from incident.domain.model.valueobjects.IncidentValueObjects import IncidentStatus


class CreateIncidentRequest(BaseModel):
    """DTO for submitting a new incident via natural language"""
    raw_input: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Raw natural language description of the issue (can be informal or incomplete)",
    )

    @field_validator("raw_input")
    @classmethod
    def raw_input_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_input cannot be blank")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "raw_input": (
                        "hola, desde esta mañana no puedo conectarme a la VPN, "
                        "necesito trabajar desde casa y es urgente"
                    )
                }
            ]
        }
    }


class StartProgressRequest(BaseModel):
    """DTO for assigning and beginning work on an incident"""
    agent_id: int = Field(..., ge=1, description="User ID of the support agent")

    model_config = {
        "json_schema_extra": {"examples": [{"agent_id": 3}]}
    }


class EscalateIncidentRequest(BaseModel):
    """DTO for escalating an incident to a higher support tier"""
    notes: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Manual notes from the escalating agent explaining why escalation is needed",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"notes": "Issue persists after L1 troubleshooting. Requires DB admin access."}
            ]
        }
    }


class ReopenIncidentRequest(BaseModel):
    """DTO for reopening a resolved or closed incident"""
    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Reason for reopening the incident",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"reason": "Issue reappeared after the fix was applied yesterday."}]
        }
    }


class ReanalyzeIncidentRequest(BaseModel):
    """DTO for triggering a fresh GenIA analysis on an existing incident"""
    additional_context: str | None = Field(
        None,
        max_length=2000,
        description="Optional extra context to enrich the re-analysis",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "additional_context": (
                        "User confirmed the issue started after a Windows update last night."
                    )
                }
            ]
        }
    }


class IncidentFilterRequest(BaseModel):
    """Query params for filtering incident lists"""
    status: IncidentStatus | None = None
    priority: str | None = None
    category: str | None = None
    incident_type: str | None = None
    reporter_id: int | None = None
    assigned_to_id: int | None = None
    is_recurring: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
