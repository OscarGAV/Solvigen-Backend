from datetime import datetime
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """DTO for user data (without password)"""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str | None = Field(None, description="Full name")
    is_active: bool = Field(..., description="Account status")
    created_at: datetime = Field(..., description="Registration date")
    updated_at: datetime = Field(..., description="Last update date")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "johndoe",
                    "email": "john@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "created_at": "2025-01-05T10:00:00Z",
                    "updated_at": "2025-01-05T10:00:00Z"
                }
            ]
        }
    }


class AuthenticationResponse(BaseModel):
    """DTO for authentication response"""
    user: UserResponse
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user": {
                        "id": 1,
                        "username": "johndoe",
                        "email": "john@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "created_at": "2025-01-05T10:00:00Z",
                        "updated_at": "2025-01-05T10:00:00Z"
                    },
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """DTO for token refresh response"""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")