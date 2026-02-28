from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from iam.application.internal.commandservice.CommandServiceImpl import CommandServiceImpl
from iam.application.internal.queryservice.QueryServiceImpl import QueryServiceImpl
from iam.domain.model.aggregates.User import User
from iam.infrastructure.persistence.repositories.UserRepositoryImpl import UserRepositoryImpl
from iam.infrastructure.tokenservice.jwt.BearerTokenService import (
    get_current_user,
    get_current_active_user
)
from iam.interface.api.rest.assemblers.AuthResourceAssembler import AuthResourceAssembler
from iam.interface.api.rest.resources.AuthRequestResource import (
    SignUpRequest,
    SignInRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    RefreshTokenRequest
)
from iam.interface.api.rest.resources.AuthResponseResource import (
    UserResponse,
    AuthenticationResponse,
    TokenResponse
)
from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# =============================================================================
# AUTHENTICATION COMMANDS (Public)
# =============================================================================

@router.post(
    "/signup",
    response_model=AuthenticationResponse,
    status_code=201,
    summary="Register new user",
    description="Create a new user account and return JWT tokens",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid request or username/email already exists"},
        500: {"description": "Internal server error"}
    }
)
async def sign_up(
        request: SignUpRequest,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Register a new user

    - **username**: Unique username (3-50 chars, alphanumeric)
    - **email**: Unique email address
    - **password**: Password (minimum 8 characters)
    - **full_name**: Optional full name

    Returns user data and JWT tokens (access + refresh)
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        command = AuthResourceAssembler.to_sign_up_command(request)
        auth_response = await service.sign_up(command)

        return AuthResourceAssembler.to_authentication_response(auth_response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/signin",
    response_model=AuthenticationResponse,
    summary="Sign in user",
    description="Authenticate user and return JWT tokens",
    responses={
        200: {"description": "Authentication successful"},
        401: {"description": "Invalid credentials or account deactivated"},
        500: {"description": "Internal server error"}
    }
)
async def sign_in(
        request: SignInRequest,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate user

    - **username_or_email**: Username or email address
    - **password**: User password

    Returns user data and JWT tokens (access + refresh)
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        command = AuthResourceAssembler.to_sign_in_command(request)
        auth_response = await service.sign_in(command)

        return AuthResourceAssembler.to_authentication_response(auth_response)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Generate new access token using refresh token",
    responses={
        200: {"description": "New access token generated"},
        401: {"description": "Invalid or expired refresh token"},
        500: {"description": "Internal server error"}
    }
)
async def refresh_token(
        request: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Refresh access token

    - **refresh_token**: Valid refresh token

    Returns new access token
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        access_token = await service.refresh_access_token(request.refresh_token)

        return TokenResponse(access_token=access_token, token_type="Bearer")

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# USER MANAGEMENT COMMANDS (Protected)
# =============================================================================

@router.post(
    "/change-password",
    response_model=UserResponse,
    summary="Change password",
    description="Change current user's password",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid old password or validation error"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def change_password(
        request: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Change user password

    Requires authentication. User must provide correct current password.

    - **old_password**: Current password
    - **new_password**: New password (min 8 chars)
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        command = AuthResourceAssembler.to_change_password_command(
            current_user.id,
            request
        )
        user = await service.change_password(command)

        return AuthResourceAssembler.to_user_response(user)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update profile",
    description="Update current user's profile information",
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"description": "Invalid request or email already exists"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def update_profile(
        request: UpdateProfileRequest,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Update user profile

    Requires authentication.

    - **full_name**: New full name (optional)
    - **email**: New email address (optional, must be unique)
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        command = AuthResourceAssembler.to_update_profile_command(
            current_user.id,
            request
        )
        user = await service.update_profile(command)

        return AuthResourceAssembler.to_user_response(user)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete(
    "/deactivate",
    status_code=204,
    summary="Deactivate account",
    description="Deactivate current user's account",
    responses={
        204: {"description": "Account deactivated successfully"},
        400: {"description": "Account already deactivated"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def deactivate_account(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Deactivate user account

    Requires authentication. User won't be able to sign in after deactivation.
    """
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)

        command = AuthResourceAssembler.to_deactivate_command(current_user.id)
        await service.deactivate_user(command)

        return None

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# USER QUERIES (Protected)
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user's information",
    responses={
        200: {"description": "User data retrieved"},
        401: {"description": "Authentication required"}
    }
)
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information

    Requires authentication. Returns user data based on JWT token.
    """
    return AuthResourceAssembler.to_user_response(current_user)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get specific user by ID (public profile)",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
async def get_user(
        user_id: int = Path(..., ge=1, description="User ID to retrieve"),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Get user by ID

    Returns public user information (no password).
    """
    repository = UserRepositoryImpl(db)
    service = QueryServiceImpl(repository)

    query = AuthResourceAssembler.to_get_by_id_query(user_id)
    user = await service.get_user_by_id(query)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return AuthResourceAssembler.to_user_response(user)