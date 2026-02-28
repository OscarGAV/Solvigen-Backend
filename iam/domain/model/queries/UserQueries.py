from dataclasses import dataclass


@dataclass(frozen=True)
class GetUserByIdQuery:
    """Query: Get user by ID"""
    user_id: int


@dataclass(frozen=True)
class GetUserByUsernameQuery:
    """Query: Get user by username"""
    username: str


@dataclass(frozen=True)
class GetUserByEmailQuery:
    """Query: Get user by email"""
    email: str


@dataclass(frozen=True)
class GetAllUsersQuery:
    """Query: Get all users (admin only)"""
    pass