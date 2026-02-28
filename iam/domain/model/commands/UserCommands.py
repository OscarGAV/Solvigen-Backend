from dataclasses import dataclass


@dataclass(frozen=True)
class SignUpCommand:
    """
    Command: Register a new user
    """
    username: str
    email: str
    password: str
    full_name: str | None = None


@dataclass(frozen=True)
class SignInCommand:
    """
    Command: Authenticate user
    Can use either username or email
    """
    username_or_email: str
    password: str


@dataclass(frozen=True)
class ChangePasswordCommand:
    """
    Command: Change user password
    """
    user_id: int
    old_password: str
    new_password: str


@dataclass(frozen=True)
class UpdateProfileCommand:
    """
    Command: Update user profile
    """
    user_id: int
    full_name: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class DeactivateUserCommand:
    """
    Command: Deactivate user account
    """
    user_id: int