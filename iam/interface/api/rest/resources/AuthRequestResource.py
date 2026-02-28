from pydantic import BaseModel, Field, field_validator


class SignUpRequest(BaseModel):
    """DTO for user registration"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    full_name: str | None = Field(None, max_length=200, description="Full name (optional)")

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (can include _ and -)')
        return v.lower().strip()

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "email": "john@example.com",
                    "password": "SecurePass123!",
                    "full_name": "John Doe"
                }
            ]
        }
    }


class SignInRequest(BaseModel):
    """DTO for user authentication"""
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username_or_email": "johndoe",
                    "password": "SecurePass123!"
                }
            ]
        }
    }


class ChangePasswordRequest(BaseModel):
    """DTO for password change"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "old_password": "OldPass123!",
                    "new_password": "NewSecurePass456!"
                }
            ]
        }
    }


class UpdateProfileRequest(BaseModel):
    """DTO for profile update"""
    full_name: str | None = Field(None, max_length=200)
    email: str | None = Field(None)

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str | None) -> str | None:
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip() if v else None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "John Doe Updated",
                    "email": "newemail@example.com"
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """DTO for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")