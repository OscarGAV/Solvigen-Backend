from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from shared.infrastructure.persistence.configuration.database_configuration import Base
import bcrypt


def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Aggregate Root: Usuario del sistema IAM
    Maneja autenticación
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # =========================================================================
    # DOMAIN LOGIC - Password Management
    # =========================================================================

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """
        Hash password using bcrypt
        """
        if not plain_password or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str) -> bool:
        """
        Verify password against stored hash
        """
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            self.hashed_password.encode('utf-8')
        )

    def change_password(self, old_password: str, new_password: str) -> None:
        """
        Change user password with verification
        """
        if not self.verify_password(old_password):
            raise ValueError("Current password is incorrect")

        self.hashed_password = self.hash_password(new_password)
        self.updated_at = utc_now()

    # =========================================================================
    # DOMAIN LOGIC - Account Management
    # =========================================================================

    def deactivate(self) -> None:
        """Deactivate user account"""
        if not self.is_active:
            raise ValueError("User account is already deactivated")

        self.is_active = False
        self.updated_at = utc_now()

    def activate(self) -> None:
        """Activate user account"""
        if self.is_active:
            raise ValueError("User account is already active")

        self.is_active = True
        self.updated_at = utc_now()

    def update_profile(self, full_name: str | None = None, email: str | None = None) -> None:
        """Update user profile information"""
        if full_name is not None:
            self.full_name = full_name

        if email is not None:
            if not email or '@' not in email:
                raise ValueError("Invalid email format")
            self.email = email

        self.updated_at = utc_now()

    # =========================================================================
    # BUSINESS RULES
    # =========================================================================

    def can_authenticate(self) -> bool:
        """Check if user can authenticate"""
        return self.is_active

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> dict:
        """Serialize user data (excluding password)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }