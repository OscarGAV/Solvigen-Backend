from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from iam.application.internal.commandservice.CommandServiceImpl import CommandServiceImpl
from iam.application.internal.queryservice.QueryServiceImpl import QueryServiceImpl
from iam.domain.model.aggregates.User import User, UserRole
from iam.infrastructure.persistence.repositories.UserRepositoryImpl import UserRepositoryImpl
from iam.infrastructure.tokenservice.jwt.BearerTokenService import get_current_active_user
from iam.interface.api.rest.assemblers.AuthResourceAssembler import AuthResourceAssembler
from iam.interface.api.rest.resources.AuthRequestResource import (
    AdminCreateUserRequest,
    AdminChangeRoleRequest,
    AdminUpdateProfileRequest,
    AdminForcePasswordResetRequest,
)
from iam.interface.api.rest.resources.AuthResponseResource import UserResponse
from shared.infrastructure.persistence.configuration.database_configuration import get_db_session

router = APIRouter(prefix="/api/v1/admin", tags=["Admin — User Management"])


# =============================================================================
# DEPENDENCY — Require admin role
# =============================================================================

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


# =============================================================================
# READ
# =============================================================================

@router.get("/users", response_model=list[UserResponse], summary="List all users")
async def list_users(
    role: UserRole | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    suspended_only: bool = Query(False, description="Show only suspended accounts"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = QueryServiceImpl(repository)
        query = AuthResourceAssembler.to_get_all_query(
            role=role, is_active=is_active, suspended_only=suspended_only
        )
        users = await service.get_all_users(query)
        return [AuthResourceAssembler.to_user_response(u) for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(
    user_id: int = Path(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = QueryServiceImpl(repository)
        query = AuthResourceAssembler.to_get_by_id_query(user_id)
        user = await service.get_user_by_id(query)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return AuthResourceAssembler.to_user_response(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/users/suspended/expired",
    response_model=list[UserResponse],
    summary="Users past 30-day grace period (ready for permanent deletion)",
)
async def get_expired_suspensions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = QueryServiceImpl(repository)
        query = AuthResourceAssembler.to_get_suspended_past_grace_query()
        users = await service.get_suspended_past_grace(query)
        return [AuthResourceAssembler.to_user_response(u) for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# CREATE
# =============================================================================

@router.post("/users", response_model=UserResponse, status_code=201, summary="Create new user")
async def create_user(
    request: AdminCreateUserRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_create_user_command(request)
        user = await service.admin_create_user(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# ROLE
# =============================================================================

@router.patch("/users/{user_id}/role", response_model=UserResponse, summary="Change user role")
async def change_role(
    request: AdminChangeRoleRequest,
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_change_role_command(user_id, request, admin.id)
        user = await service.admin_change_role(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# PROFILE & PASSWORD PERMISSIONS
# =============================================================================

@router.patch(
    "/users/{user_id}/grant-profile",
    response_model=UserResponse,
    summary="Grant profile edit permission",
)
async def grant_profile_edit(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_grant_profile_command(user_id, admin.id)
        user = await service.admin_grant_profile_edit(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/users/{user_id}/revoke-profile",
    response_model=UserResponse,
    summary="Revoke profile edit permission",
)
async def revoke_profile_edit(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_revoke_profile_command(user_id, admin.id)
        user = await service.admin_revoke_profile_edit(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/users/{user_id}/grant-password",
    response_model=UserResponse,
    summary="Grant password change permission",
)
async def grant_password_change(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_grant_password_command(user_id, admin.id)
        user = await service.admin_grant_password_change(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/users/{user_id}/revoke-password",
    response_model=UserResponse,
    summary="Revoke password change permission",
)
async def revoke_password_change(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_revoke_password_command(user_id, admin.id)
        user = await service.admin_revoke_password_change(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# PROFILE & PASSWORD DIRECT EDIT (admin)
# =============================================================================

@router.put(
    "/users/{user_id}/profile",
    response_model=UserResponse,
    summary="Admin updates any user's profile directly",
)
async def admin_update_profile(
    request: AdminUpdateProfileRequest,
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_update_profile_command(user_id, request, admin.id)
        user = await service.admin_update_profile(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/users/{user_id}/reset-password",
    response_model=UserResponse,
    summary="Admin resets a user's password directly",
)
async def admin_reset_password(
    request: AdminForcePasswordResetRequest,
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_force_password_reset_command(user_id, request, admin.id)
        user = await service.admin_force_password_reset(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# SUSPENSION LIFECYCLE
# =============================================================================

@router.patch(
    "/users/{user_id}/suspend",
    response_model=UserResponse,
    summary="Suspend user account (starts 30-day grace period)",
)
async def suspend_user(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_suspend_command(user_id, admin.id)
        user = await service.admin_suspend_user(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.patch(
    "/users/{user_id}/reactivate",
    response_model=UserResponse,
    summary="Reactivate suspended user (within 30-day grace period)",
)
async def reactivate_user(
    user_id: int = Path(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        service = CommandServiceImpl(repository)
        command = AuthResourceAssembler.to_admin_reactivate_command(user_id, admin.id)
        user = await service.admin_reactivate_user(command)
        return AuthResourceAssembler.to_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Permanently delete user (only after 30-day grace period)",
)
async def delete_user(
    user_id: int = Path(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        repository = UserRepositoryImpl(db)
        query_service = QueryServiceImpl(repository)

        user = await query_service.get_user_by_id(
            AuthResourceAssembler.to_get_by_id_query(user_id)
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_admin():
            raise HTTPException(status_code=403, detail="Cannot delete an admin account")
        if user.is_active:
            raise HTTPException(status_code=400, detail="Cannot delete an active account — suspend first")
        if not user.is_past_grace_period():
            days_left = user.days_until_deletion()
            raise HTTPException(
                status_code=400,
                detail=f"Grace period not expired — {days_left} day(s) remaining",
            )

        await repository.delete(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")