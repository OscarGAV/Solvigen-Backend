"""
Resolution Controller — flujo de confirmación de resolución de incidentes.

Endpoints:
  PATCH /api/v1/incidents/{incident_id}/request-resolution
      → Agente solicita confirmación al end_user reporter

  GET   /api/v1/notifications/resolution-requests
      → End user ve sus solicitudes de confirmación pendientes

  PATCH /api/v1/notifications/resolution-requests/{id}/respond
      → End user responde (confirmed / rejected)

  GET   /api/v1/notifications/resolution-responses
      → Agentes ven las respuestas de los end users
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iam.domain.model.aggregates.User import User, UserRole
from iam.infrastructure.tokenservice.jwt.BearerTokenService import get_current_active_user
from notification.domain.model.aggregates.NotificationModel import Notification, NotificationType
from incident.domain.model.aggregates.Resolution import (
    ResolutionRequest,
    ResolutionStatus,
)
from incident.domain.model.aggregates.Incident import Incident
from incident.domain.model.valueobjects.IncidentValueObjects import IncidentStatus
from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

router = APIRouter(prefix="/api/v1", tags=["Resolution"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# SCHEMAS
# =============================================================================

class ResolutionRequestResponse(BaseModel):
    id: int
    incident_id: int
    incident_title: str
    agent_id: int
    agent_username: str
    agent_fullname: str
    reporter_id: int
    status: str
    agent_notified: bool
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


class RespondResolutionRequest(BaseModel):
    confirmed: bool


# =============================================================================
# ROLE DEPENDENCIES
# =============================================================================

_AGENT_ROLES = {UserRole.L1_AGENT, UserRole.L2_AGENT, UserRole.IT_MANAGER}


async def require_agent(current_user: User = Depends(get_current_active_user)) -> User:
    """Permite acceso solo a l1_agent, l2_agent e it_manager."""
    if current_user.role not in _AGENT_ROLES:
        raise HTTPException(status_code=403, detail="Agent role required")
    return current_user


async def require_end_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Permite acceso solo a end_user."""
    if current_user.role != UserRole.END_USER:
        raise HTTPException(status_code=403, detail="End user role required")
    return current_user


# =============================================================================
# ENDPOINT 1 — Agente solicita confirmación de resolución
# =============================================================================

@router.patch(
    "/incidents/{incident_id}/request-resolution",
    response_model=ResolutionRequestResponse,
    status_code=201,
    summary="Solicitar confirmación de resolución al reporter",
)
async def request_resolution(
    incident_id: int = Path(..., ge=1),
    current_user: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db_session),
):
    """
    El agente indica que el incidente está resuelto técnicamente y solicita
    confirmación al end_user que lo reportó. No cambia el status del incidente.

    - Solo accesible por agentes (l1_agent, l2_agent, it_manager).
    - Retorna 404 si el incidente no existe.
    - Retorna 409 si ya existe una solicitud pendiente para este incidente.
    """
    # Verificar que el incidente existe
    inc_result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = inc_result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incidente {incident_id} no encontrado")

    # Verificar que el reporter es end_user
    from iam.domain.model.aggregates.User import UserRole
    reporter_result = await db.execute(select(User).where(User.id == incident.reporter_id))
    reporter = reporter_result.scalar_one_or_none()
    if not reporter or reporter.role != UserRole.END_USER:
        raise HTTPException(
            status_code=400,
            detail="El reporter del incidente no es un end_user",
        )

    # Verificar que no existe ya una solicitud pendiente para este incidente
    existing = await db.execute(
        select(ResolutionRequest).where(
            ResolutionRequest.incident_id == incident_id,
            ResolutionRequest.status == ResolutionStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Ya existe una solicitud de confirmación pendiente para este incidente",
        )

    # Crear ResolutionRequest
    resolution_req = ResolutionRequest(
        incident_id=incident_id,
        incident_title=incident.title,
        agent_id=current_user.id,
        agent_username=current_user.username,
        agent_fullname=current_user.full_name or current_user.username,
        reporter_id=incident.reporter_id,
        status=ResolutionStatus.PENDING,
        agent_notified=False,
    )
    db.add(resolution_req)

    # Crear Notification para el reporter
    notification = Notification(
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_fullname=current_user.full_name or current_user.username,
        notification_type=NotificationType.RESOLUTION_REQUEST,
        message=(
            f"{current_user.full_name or current_user.username} indica que el incidente "
            f'"{incident.title}" ha sido resuelto. Por favor confirma si el problema fue solucionado.'
        ),
    )
    db.add(notification)

    await db.commit()
    await db.refresh(resolution_req)
    return resolution_req


# =============================================================================
# ENDPOINT 2 — End user ve sus solicitudes de confirmación
# =============================================================================

@router.get(
    "/notifications/resolution-requests",
    response_model=List[ResolutionRequestResponse],
    summary="Ver solicitudes de confirmación pendientes",
)
async def get_resolution_requests(
    incident_id: Optional[int] = Query(None, description="Filtrar por ID de incidente"),
    current_user: User = Depends(require_end_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    El end_user consulta las solicitudes de confirmación de resolución que le corresponden.

    - Solo accesible por end_user.
    - Filtra automáticamente por reporter_id = usuario actual.
    - Acepta el parámetro opcional incident_id para filtrar por incidente.
    - Ordenado por created_at desc.
    """
    stmt = (
        select(ResolutionRequest)
        .where(
            ResolutionRequest.reporter_id == current_user.id,
            ResolutionRequest.status == ResolutionStatus.PENDING,  # solo las pendientes
        )
        .order_by(ResolutionRequest.created_at.desc())
    )
    if incident_id is not None:
        stmt = stmt.where(ResolutionRequest.incident_id == incident_id)

    result = await db.execute(stmt)
    return result.scalars().all()


# =============================================================================
# ENDPOINT 3 — End user responde a la solicitud
# =============================================================================

@router.patch(
    "/notifications/resolution-requests/{resolution_id}/respond",
    response_model=ResolutionRequestResponse,
    summary="Responder a una solicitud de confirmación de resolución",
)
async def respond_resolution_request(
    body: RespondResolutionRequest,
    resolution_id: int = Path(..., ge=1),
    current_user: User = Depends(require_end_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    El end_user confirma o rechaza la resolución del incidente.

    - body.confirmed=true  → el incidente pasa a status RESOLVED
    - body.confirmed=false → el status del incidente no cambia
    - En ambos casos se crea una Notification para el agente asignado.
    - Retorna 404 si la solicitud no existe.
    - Retorna 403 si el usuario no es el reporter del incidente.
    - Retorna 409 si la solicitud ya fue respondida.
    """
    # Cargar la ResolutionRequest
    rr_result = await db.execute(
        select(ResolutionRequest).where(ResolutionRequest.id == resolution_id)
    )
    resolution_req = rr_result.scalar_one_or_none()
    if not resolution_req:
        raise HTTPException(status_code=404, detail="Solicitud de resolución no encontrada")

    # Verificar que el current_user es el reporter
    if resolution_req.reporter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para responder esta solicitud",
        )

    # Verificar que aún está pendiente
    if resolution_req.status != ResolutionStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="Esta solicitud ya fue respondida anteriormente",
        )

    # Actualizar estado de la solicitud
    resolution_req.status = ResolutionStatus.CONFIRMED if body.confirmed else ResolutionStatus.REJECTED
    resolution_req.responded_at = utc_now()

    # Si confirma → cambiar el status del incidente a RESOLVED
    if body.confirmed:
        inc_result = await db.execute(
            select(Incident).where(Incident.id == resolution_req.incident_id)
        )
        incident = inc_result.scalar_one_or_none()
        if incident:
            incident.status = IncidentStatus.RESOLVED

    # Crear Notification para el agente
    reporter_name = current_user.full_name or current_user.username
    if body.confirmed:
        msg = (
            f'{reporter_name} ha confirmado que el incidente '
            f'"{resolution_req.incident_title}" fue resuelto correctamente.'
        )
    else:
        msg = (
            f'{reporter_name} indicó que el incidente '
            f'"{resolution_req.incident_title}" NO fue resuelto. Se requiere seguimiento.'
        )

    agent_notification = Notification(
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_fullname=reporter_name,
        notification_type=NotificationType.RESOLUTION_RESPONSE,
        message=msg,
    )
    db.add(agent_notification)
    resolution_req.agent_notified = True

    await db.commit()
    await db.refresh(resolution_req)
    return resolution_req


# =============================================================================
# ENDPOINT 4 — Agentes ven las respuestas del end user
# =============================================================================

@router.get(
    "/notifications/resolution-responses",
    response_model=List[ResolutionRequestResponse],
    summary="Ver respuestas de confirmación de end users",
)
async def get_resolution_responses(
    incident_id: Optional[int] = Query(None, description="Filtrar por ID de incidente"),
    current_user: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Los agentes consultan las respuestas de confirmación recibidas de los end users.

    - Solo accesible por agentes (l1_agent, l2_agent, it_manager).
    - Filtra automáticamente por agent_id = usuario actual.
    - Acepta el parámetro opcional incident_id para filtrar por incidente.
    - Ordenado por created_at desc.
    """
    stmt = (
        select(ResolutionRequest)
        .where(ResolutionRequest.agent_id == current_user.id)
        .order_by(ResolutionRequest.created_at.desc())
    )
    if incident_id is not None:
        stmt = stmt.where(ResolutionRequest.incident_id == incident_id)

    result = await db.execute(stmt)
    return result.scalars().all()