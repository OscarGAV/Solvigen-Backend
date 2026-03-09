"""
Notification domain model for permission request messages.
Users send permission requests → Admin sees them in the activity feed.
"""

from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.configuration.database_configuration import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationType(str, Enum):
    PROFILE_EDIT_REQUEST  = "profile_edit_request"
    PASSWORD_CHANGE_REQUEST = "password_change_request"
    RESOLUTION_REQUEST      = "resolution_request"   # ← NUEVO: TI Team → end_user
    RESOLUTION_RESPONSE     = "resolution_response"  # ← NUEVO: end_user → TI Team


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Who sent the request
    sender_id:       Mapped[int]    = mapped_column(Integer, nullable=False)
    sender_username: Mapped[str]    = mapped_column(String(100), nullable=False)
    sender_fullname: Mapped[str]    = mapped_column(String(255), nullable=False)

    # What they're requesting
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)

    # State
    is_read:    Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)