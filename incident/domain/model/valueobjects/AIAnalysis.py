from dataclasses import dataclass, field

from incident.domain.model.valueobjects.IncidentValueObjects import (
    IncidentType,
    Category,
    Priority,
)


@dataclass
class AIAnalysis:
    """
    Value Object: Structured output produced by the GenIA agent pipeline.
    Captures the classification, prioritization rationale, and suggested
    response generated for each incident.
    """
    incident_type: IncidentType
    category: Category
    priority: Priority

    # Explainability — why did the AI decide this?
    classification_reason: str      # Agente Clasificador explanation
    priority_reason: str            # Agente Priorizacion explanation

    # Agente Soporte output
    suggested_response: str         # Draft response for the end user

    # Agente Analitico output (populated on recurrence detection)
    is_recurring: bool = False
    recurrence_count: int = 0
    root_cause_hypothesis: str | None = None
    preventive_actions: list[str] = field(default_factory=list)

    # Confidence scores [0.0 – 1.0]
    classification_confidence: float = 0.0
    priority_confidence: float = 0.0
