"""
Notification Controller
- POST /api/v1/notifications/request-profile   → any user sends profile edit request
- POST /api/v1/notifications/request-password  → any user sends password change request
- GET  /api/v1/notifications                   → admin sees all notifications
- PATCH /api/v1/notifications/{id}/read        → admin marks as read
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from iam.domain.model.aggregates.User import User
from iam.infrastructure.tokenservice.jwt.BearerTokenService import get_current_active_user
from notification.domain.model.aggregates.NotificationModel import (Notification, NotificationType)
from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


# =============================================================================
# SCHEMAS
# =============================================================================

class NotificationResponse(BaseModel):
    id: int
    sender_id: int
    sender_username: str
    sender_fullname: str
    notification_type: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# HELPERS
# =============================================================================

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


async def _create_notification(
    db: AsyncSession,
    user: User,
    notification_type: NotificationType,
    message: str,
) -> Notification:
    notif = Notification(
        sender_id=user.id,
        sender_username=user.username,
        sender_fullname=user.full_name or user.username,
        notification_type=notification_type,
        message=message,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


# =============================================================================
# USER ENDPOINTS — send permission requests
# =============================================================================

@router.post("/request-profile", response_model=NotificationResponse, status_code=201)
async def request_profile_edit(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """User requests permission to edit their profile."""
    if current_user.can_edit_profile:
        raise HTTPException(status_code=400, detail="You already have permission to edit your profile")

    notif = await _create_notification(
        db, current_user,
        NotificationType.PROFILE_EDIT_REQUEST,
        f"{current_user.full_name or current_user.username} solicita permiso para editar su perfil.",
    )
    return notif


@router.post("/request-password", response_model=NotificationResponse, status_code=201)
async def request_password_change(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """User requests permission to change their password."""
    if current_user.can_change_password:
        raise HTTPException(status_code=400, detail="You already have permission to change your password")

    notif = await _create_notification(
        db, current_user,
        NotificationType.PASSWORD_CHANGE_REQUEST,
        f"{current_user.full_name or current_user.username} solicita permiso para cambiar su contraseña.",
    )
    return notif


# =============================================================================
# ADMIN ENDPOINTS — view and manage notifications
# =============================================================================

@router.get("", response_model=List[NotificationResponse])
async def get_all_notifications(
    unread_only: bool = False,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Admin retrieves all permission request notifications."""
    stmt = (
        select(Notification)
        .where(Notification.notification_type.notin_([
            NotificationType.RESOLUTION_REQUEST,
            NotificationType.RESOLUTION_RESPONSE,
        ]))
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Admin marks a notification as read."""
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif


@router.patch("/read-all")
async def mark_all_read(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Admin marks all notifications as read."""
    await db.execute(
        update(Notification).where(Notification.is_read == False).values(is_read=True)  # noqa: E712
    )
    await db.commit()
    return {"detail": "All notifications marked as read"}