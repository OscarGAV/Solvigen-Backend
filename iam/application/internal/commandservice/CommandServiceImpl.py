from iam.domain.model.aggregates.User import User
from iam.domain.model.commands.UserCommands import (
    SignUpCommand,
    SignInCommand,
    ChangePasswordCommand,
    UpdateProfileCommand,
    DeactivateUserCommand
)
from iam.domain.repositories.UserRepository import UserRepository
from iam.application.internal.tokenservice.JWTService import jwt_service


class AuthenticationResponse:
    """Response for authentication operations"""

    def __init__(self, user: User, access_token: str, refresh_token: str):
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token


class CommandServiceImpl:
    """
    Command Service for IAM Context
    Handles all write operations (sign up, sign in, password changes, etc.)
    """

    def __init__(self, repository: UserRepository):
        self._repository = repository

    async def sign_up(self, command: SignUpCommand) -> AuthenticationResponse:
        """
        Register new user

        Business Rules:
        - Username must be unique
        - Email must be unique
        - Password must be at least 8 characters
        """

        # Validate username uniqueness
        if await self._repository.exists_by_username(command.username):
            raise ValueError(f"Username '{command.username}' is already taken")

        # Validate email uniqueness
        if await self._repository.exists_by_email(command.email):
            raise ValueError(f"Email '{command.email}' is already registered")

        # Validate email format
        if '@' not in command.email:
            raise ValueError("Invalid email format")

        # Validate username format
        if len(command.username) < 3 or len(command.username) > 50:
            raise ValueError("Username must be between 3 and 50 characters")

        # Create user aggregate
        user = User(
            username=command.username.lower().strip(),
            email=command.email.lower().strip(),
            hashed_password=User.hash_password(command.password),
            full_name=command.full_name,
            is_active=True
        )

        # Persist
        saved_user = await self._repository.save(user)

        # Generate JWT tokens
        access_token = jwt_service.create_access_token(
            user_id=saved_user.id,
            username=saved_user.username,
            email=saved_user.email
        )
        refresh_token = jwt_service.create_refresh_token(user_id=saved_user.id)

        return AuthenticationResponse(saved_user, access_token, refresh_token)

    async def sign_in(self, command: SignInCommand) -> AuthenticationResponse:
        """
        Authenticate user

        Business Rules:
        - User must exist
        - Password must be correct
        - Account must be active
        """

        # Find user by username or email
        user = await self._repository.find_by_username_or_email(
            command.username_or_email.lower().strip()
        )

        if not user:
            raise ValueError("Invalid credentials")

        # Verify password
        if not user.verify_password(command.password):
            raise ValueError("Invalid credentials")

        # Check if user can authenticate
        if not user.can_authenticate():
            raise ValueError("Account is deactivated")

        # Generate JWT tokens
        access_token = jwt_service.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email
        )
        refresh_token = jwt_service.create_refresh_token(user_id=user.id)

        return AuthenticationResponse(user, access_token, refresh_token)

    async def change_password(self, command: ChangePasswordCommand) -> User:
        """
        Change user password
        """
        user = await self._repository.find_by_id(command.user_id)

        if not user:
            raise ValueError(f"User not found: {command.user_id}")

        # Use domain logic for password change
        user.change_password(command.old_password, command.new_password)

        return await self._repository.save(user)

    async def update_profile(self, command: UpdateProfileCommand) -> User:
        """
        Update user profile
        """
        user = await self._repository.find_by_id(command.user_id)

        if not user:
            raise ValueError(f"User not found: {command.user_id}")

        # Check email uniqueness if changing email
        if command.email and command.email != user.email:
            if await self._repository.exists_by_email(command.email):
                raise ValueError(f"Email '{command.email}' is already registered")

        # Use domain logic for profile update
        user.update_profile(full_name=command.full_name, email=command.email)

        return await self._repository.save(user)

    async def deactivate_user(self, command: DeactivateUserCommand) -> User:
        """
        Deactivate user account
        """
        user = await self._repository.find_by_id(command.user_id)

        if not user:
            raise ValueError(f"User not found: {command.user_id}")

        user.deactivate()

        return await self._repository.save(user)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token
        """
        try:
            user_id = jwt_service.get_user_id_from_token(refresh_token)
        except ValueError:
            raise ValueError("Invalid or expired refresh token")

        user = await self._repository.find_by_id(user_id)

        if not user or not user.can_authenticate():
            raise ValueError("User not found or account deactivated")

        # Generate new access token
        access_token = jwt_service.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email
        )

        return access_token