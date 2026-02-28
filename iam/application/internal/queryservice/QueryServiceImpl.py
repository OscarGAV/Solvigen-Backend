from iam.domain.model.aggregates.User import User
from iam.domain.model.queries.UserQueries import (
    GetUserByIdQuery,
    GetUserByUsernameQuery,
    GetUserByEmailQuery
)
from iam.domain.repositories.UserRepository import UserRepository


class QueryServiceImpl:
    """
    Query Service for IAM Context
    Handles all read operations (CQRS pattern)
    """

    def __init__(self, repository: UserRepository):
        self._repository = repository

    async def get_user_by_id(self, query: GetUserByIdQuery) -> User | None:
        """Get user by ID"""
        return await self._repository.find_by_id(query.user_id)

    async def get_user_by_username(self, query: GetUserByUsernameQuery) -> User | None:
        """Get user by username"""
        return await self._repository.find_by_username(query.username)

    async def get_user_by_email(self, query: GetUserByEmailQuery) -> User | None:
        """Get user by email"""
        return await self._repository.find_by_email(query.email)

    async def get_all_users(self) -> list[User]:
        """Get all users (admin only)"""
        return await self._repository.find_all()