from datetime import datetime, timezone
from enum import Enum

import bcrypt
from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.configuration.database_configuration import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    END_USER    = "end_user"
    L1_AGENT    = "l1_agent"
    L2_AGENT    = "l2_agent"
    IT_MANAGER  = "it_manager"
    ADMIN       = "admin"


SUSPENSION_GRACE_DAYS = 30


class User(Base):
    """
    Aggregate Root: Usuario del sistema IAM
    Maneja autenticación, roles y permisos de edición.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # ── Roles ────────────────────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, default=UserRole.END_USER
    )

    # ── Permisos de edición (concedidos por admin) ────────────────────────────
    can_edit_profile: Mapped[bool] = mapped_column(default=False)
    can_change_password: Mapped[bool] = mapped_column(default=False)

    # ── Suspensión con gracia de 30 días ─────────────────────────────────────
    suspended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # =========================================================================
    # DOMAIN LOGIC — Password
    # =========================================================================

    @staticmethod
    def hash_password(plain_password: str) -> str:
        if not plain_password or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            self.hashed_password.encode('utf-8')
        )

    def change_password(self, old_password: str, new_password: str) -> None:
        """
        User changes their own password (requires prior admin permission).
        Permission is single-use — revoked automatically after the change.
        """
        if not self.can_change_password:
            raise ValueError("You do not have permission to change your password")
        if not self.verify_password(old_password):
            raise ValueError("Current password is incorrect")
        self.hashed_password = self.hash_password(new_password)
        self.can_change_password = False  # ← single-use: revoked after use
        self.updated_at = utc_now()

    def force_change_password(self, new_password: str) -> None:
        """Admin resets a user's password directly (no old password needed)."""
        self.hashed_password = self.hash_password(new_password)
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC — Profile
    # =========================================================================

    def update_profile(self, full_name: str | None = None, email: str | None = None) -> None:
        """
        User updates their own profile (requires prior admin permission).
        Permission is single-use — revoked automatically after the change.
        """
        if not self.can_edit_profile:
            raise ValueError("You do not have permission to edit your profile")
        self._apply_profile(full_name, email)
        self.can_edit_profile = False  # ← single-use: revoked after use

    def admin_update_profile(self, full_name: str | None = None, email: str | None = None) -> None:
        """Admin updates any user's profile without permission check."""
        self._apply_profile(full_name, email)

    def _apply_profile(self, full_name: str | None, email: str | None) -> None:
        if full_name is not None:
            self.full_name = full_name
        if email is not None:
            if '@' not in email:
                raise ValueError("Invalid email format")
            self.email = email
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC — Permissions (granted by admin)
    # =========================================================================

    def grant_profile_edit(self) -> None:
        self.can_edit_profile = True
        self.updated_at = utc_now()

    def revoke_profile_edit(self) -> None:
        self.can_edit_profile = False
        self.updated_at = utc_now()

    def grant_password_change(self) -> None:
        self.can_change_password = True
        self.updated_at = utc_now()

    def revoke_password_change(self) -> None:
        self.can_change_password = False
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC — Role
    # =========================================================================

    def assign_role(self, new_role: UserRole) -> None:
        if new_role == UserRole.ADMIN:
            raise ValueError("Admin role cannot be assigned through the application")
        self.role = new_role
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC — Account lifecycle
    # =========================================================================

    def suspend(self) -> None:
        """
        Suspend account. Starts the 30-day grace period.
        After 30 days the account should be permanently deleted.
        """
        if not self.is_active:
            raise ValueError("Account is already deactivated")
        if self.role == UserRole.ADMIN:
            raise ValueError("Admin account cannot be suspended through the application")
        self.is_active = False
        self.suspended_at = utc_now()
        self.updated_at = utc_now()

    def reactivate(self) -> None:
        """Cancel suspension within the 30-day grace window."""
        if self.is_active:
            raise ValueError("Account is already active")
        if self.is_past_grace_period():
            raise ValueError("Grace period expired — account must be permanently deleted")
        self.is_active = True
        self.suspended_at = None
        self.updated_at = utc_now()

    def deactivate(self) -> None:
        """Legacy deactivate (self-initiated). Kept for backwards compatibility."""
        if not self.is_active:
            raise ValueError("User account is already deactivated")
        self.is_active = False
        self.updated_at = utc_now()

    def activate(self) -> None:
        """Legacy activate. Kept for backwards compatibility."""
        if self.is_active:
            raise ValueError("User account is already active")
        self.is_active = True
        self.updated_at = utc_now()

    # =========================================================================
    # BUSINESS RULES
    # =========================================================================

    def can_authenticate(self) -> bool:
        return self.is_active

    def is_past_grace_period(self) -> bool:
        """True if suspended_at exists and 30 days have elapsed."""
        if not self.suspended_at:
            return False
        suspended = (
            self.suspended_at.replace(tzinfo=timezone.utc)
            if self.suspended_at.tzinfo is None
            else self.suspended_at
        )
        return (utc_now() - suspended).days >= SUSPENSION_GRACE_DAYS

    def days_until_deletion(self) -> int | None:
        """Days remaining in grace period. None if not suspended."""
        if not self.suspended_at:
            return None
        suspended = (
            self.suspended_at.replace(tzinfo=timezone.utc)
            if self.suspended_at.tzinfo is None
            else self.suspended_at
        )
        elapsed = (utc_now() - suspended).days
        remaining = SUSPENSION_GRACE_DAYS - elapsed
        return max(remaining, 0)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "role": self.role,
            "can_edit_profile": self.can_edit_profile,
            "can_change_password": self.can_change_password,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "days_until_deletion": self.days_until_deletion(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }