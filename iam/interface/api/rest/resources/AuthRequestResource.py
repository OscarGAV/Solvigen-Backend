from pydantic import BaseModel, Field, field_validator
from iam.domain.model.aggregates.User import UserRole


# SignUpRequest removed — public registration is disabled.
# Users are created exclusively by admins via AdminCreateUserRequest.

class SignInRequest(BaseModel):
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

    model_config = {
        "json_schema_extra": {"examples": [{"username_or_email": "johndoe", "password": "SecurePass123!"}]}
    }


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    email: str | None = None

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str | None) -> str | None:
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip() if v else None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Admin requests ────────────────────────────────────────────────────────────

class AdminCreateUserRequest(BaseModel):
    """Admin creates a new user with a role."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    role: UserRole = Field(..., description="Role to assign (cannot be 'admin')")
    full_name: str | None = Field(None, max_length=200)

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (can include _ and -)')
        return v.lower().strip()

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()

    @field_validator('role')
    @classmethod
    def role_not_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError('Admin role cannot be assigned through the API')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "username": "jsmith",
                "email": "jsmith@company.com",
                "password": "TempPass123!",
                "role": "l1_agent",
                "full_name": "John Smith"
            }]
        }
    }


class AdminChangeRoleRequest(BaseModel):
    role: UserRole = Field(..., description="New role (cannot be 'admin')")

    @field_validator('role')
    @classmethod
    def role_not_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError('Admin role cannot be assigned through the API')
        return v


class AdminUpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    email: str | None = None

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str | None) -> str | None:
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip() if v else None


class AdminForcePasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8, description="New password set by admin")