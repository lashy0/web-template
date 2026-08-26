from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.auth.permissions import Permission
from app.auth.roles import Role
from app.modules.users.models import User
from app.modules.users.schemas import (
    AuthState,
    CreateUserRequest,
    UpdateActiveRequest,
    UpdateArchivedRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from app.modules.users.service import UserManagementService

router = APIRouter(prefix="/users", tags=["users"])


def _response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        identity_id=user.identity_id,
        name=user.name,
        role=user.role,
        login=user.identity_login,
        auth_state=cast(AuthState, user.auth_state),
        auth_state_synced_at=user.auth_state_synced_at,
        archived_at=user.archived_at,
    )


def _service(request: Request) -> UserManagementService:
    return cast(UserManagementService, request.app.state.user_management)


@router.get("", response_model=UserListResponse)
async def list_users(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_READ))],
    request: Request,
    q: str | None = None,
    role: Role | None = None,
    auth_state: AuthState | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["name", "login", "created_at", "archived_at"] = "name",
    order: Literal["asc", "desc"] = "asc",
) -> UserListResponse:
    users, total = await _service(request).list(
        q=q,
        role=role,
        auth_state=auth_state,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return UserListResponse(
        items=[_response(user) for user in users], total=total, page=page, page_size=page_size
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_READ))],
    request: Request,
) -> UserResponse:
    user = await _service(request).get(user_id)
    if user is None:
        from app.auth.exceptions import IdentityNotFoundError

        raise IdentityNotFoundError
    return _response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_CREATE))],
    request: Request,
) -> UserResponse:
    user = await _service(request).create(
        actor=principal,
        name=payload.name,
        role=payload.role,
        login=payload.login,
        password=payload.password,
        active=payload.active,
    )
    return _response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_UPDATE))],
    request: Request,
) -> UserResponse:
    return _response(
        await _service(request).update(
            actor=principal,
            user_id=user_id,
            login=payload.login,
            name=payload.name,
            role=payload.role,
        )
    )


@router.put(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_password(
    user_id: UUID,
    payload: UpdatePasswordRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(Permission.USER_SET_PASSWORD)),
    ],
    request: Request,
) -> None:
    await _service(request).set_password(
        actor=principal,
        user_id=user_id,
        password=payload.password,
    )


@router.put("/{user_id}/active", response_model=UserResponse)
async def update_active(
    user_id: UUID,
    payload: UpdateActiveRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(Permission.USER_SET_ACTIVE))
    ],
    request: Request,
) -> UserResponse:
    return _response(
        await _service(request).set_active(actor=principal, user_id=user_id, active=payload.active)
    )


@router.put("/{user_id}/archived", response_model=UserResponse)
async def update_archived(
    user_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_ARCHIVE))],
    request: Request,
) -> UserResponse:
    return _response(
        await _service(request).set_archived(
            actor=principal, user_id=user_id, archived=payload.archived
        )
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(Permission.USER_DELETE))],
    request: Request,
) -> None:
    await _service(request).delete(actor=principal, user_id=user_id)
