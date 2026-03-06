from enum import Enum


class IncidentType(str, Enum):
    """
    Value Object: Type of ticket submitted
    """
    INCIDENT = "incident"       # Unexpected disruption to a service
    REQUEST = "request"         # Formal request for something new
    PROBLEM = "problem"         # Root cause of one or more incidents


class Category(str, Enum):
    """
    Value Object: Technical category of the incident
    """
    NETWORK = "network"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    ACCESS = "access"
    EMAIL = "email"
    DATABASE = "database"
    SECURITY = "security"
    OTHER = "other"


class Priority(str, Enum):
    """
    Value Object: Business impact-based priority
    P1 = Critical (SLA: 1h), P2 = High (4h), P3 = Medium (8h), P4 = Low (72h)
    """
    CRITICAL = "critical"   # P1 - Full service down, massive impact
    HIGH = "high"           # P2 - Major degradation, many users affected
    MEDIUM = "medium"       # P3 - Partial impact, workaround available
    LOW = "low"             # P4 - Minor issue, cosmetic or isolated


class IncidentStatus(str, Enum):
    """
    Value Object: Lifecycle state of an incident
    """
    OPEN = "open"               # Newly created, unassigned
    IN_PROGRESS = "in_progress" # Being actively worked on
    ESCALATED = "escalated"     # Elevated to higher support tier
    PENDING = "pending"         # Waiting on user or third party
    RESOLVED = "resolved"       # Fix applied, confirmed working
    CLOSED = "closed"           # Verified resolved, ticket closed


# SLA resolution targets in hours per priority
SLA_HOURS: dict[Priority, int] = {
    Priority.CRITICAL: 1,
    Priority.HIGH: 4,
    Priority.MEDIUM: 8,
    Priority.LOW: 72,
}
