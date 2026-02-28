from typing import Protocol
from iam.domain.model.aggregates.User import User


class UserRepository(Protocol):
    """
    Repository interface for User aggregate
    """

    async def save(self, user: User) -> User:
        """Save or update user"""
        ...

    async def find_by_id(self, user_id: int) -> User | None:
        """Find user by ID"""
        ...

    async def find_by_username(self, username: str) -> User | None:
        """Find user by username"""
        ...

    async def find_by_email(self, email: str) -> User | None:
        """Find user by email"""
        ...

    async def find_all(self) -> list[User]:
        """Find all users"""
        ...

    async def delete(self, user: User) -> None:
        """Delete user"""
        ...

    async def exists_by_username(self, username: str) -> bool:
        """Check if username exists"""
        ...

    async def exists_by_email(self, email: str) -> bool:
        """Check if email exists"""
        ...

    async def find_by_username_or_email(self, username_or_email: str) -> User | None:
        """Find user by username or email"""
        ...