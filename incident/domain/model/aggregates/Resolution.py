"""
Resolution Request domain model.

Flujo:
  Agente → crea ResolutionRequest (pending) + Notification para el reporter
  End user → responde (confirmed / rejected) → se notifica al agente
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.configuration.database_configuration import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResolutionStatus(str, Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    REJECTED  = "rejected"


class ResolutionRequest(Base):
    __tablename__ = "resolution_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Incidente relacionado
    incident_id:    Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    incident_title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Agente que solicita la confirmación
    agent_id:       Mapped[int] = mapped_column(Integer, nullable=False)
    agent_username: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_fullname: Mapped[str] = mapped_column(String(255), nullable=False)

    # End user que debe responder
    reporter_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Estado de la solicitud
    status: Mapped[ResolutionStatus] = mapped_column(
        SAEnum(ResolutionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ResolutionStatus.PENDING,
    )

    # Para saber si ya se creó la notificación de vuelta al agente
    agent_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)