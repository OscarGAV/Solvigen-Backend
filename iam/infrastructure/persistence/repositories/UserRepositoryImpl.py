from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from iam.domain.model.aggregates.User import User


class UserRepositoryImpl:
    """
    Concrete implementation of UserRepository
    Handles all database interactions for User aggregate
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, user: User) -> User:
        """Save or update user"""
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def find_by_id(self, user_id: int) -> User | None:
        """Find user by ID"""
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_username(self, username: str) -> User | None:
        """Find user by username"""
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        """Find user by email"""
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_by_username_or_email(self, username_or_email: str) -> User | None:
        """Find user by username or email"""
        result = await self._session.execute(
            select(User).where(
                or_(
                    User.username == username_or_email,
                    User.email == username_or_email
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_all(self) -> list[User]:
        """Find all users"""
        result = await self._session.execute(
            select(User).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, user: User) -> None:
        """Delete user"""
        await self._session.delete(user)
        await self._session.commit()

    async def exists_by_username(self, username: str) -> bool:
        """Check if username exists"""
        result = await self._session.execute(
            select(User.id).where(User.username == username)
        )
        return result.scalar_one_or_none() is not None

    async def exists_by_email(self, email: str) -> bool:
        """Check if email exists"""
        result = await self._session.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None