from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.shared.dependencies import SessionFactoryDep
from app.shared.security import Role
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission

from .enums import AuthState
from .exceptions import UserNotFoundError
from .permissions import UserPermission
from .presentation import user_response
from .schemas import (
    CreateUserRequest,
    UpdateActiveRequest,
    UpdateArchivedRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from .wiring import (
    IdentityProviderDep,
    create_queries,
    create_user_command,
    delete_user_command,
    set_active_command,
    set_archived_command,
    set_password_command,
    update_user_command,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    role: Role | None = None,
    auth_state: AuthState | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["name", "login", "created_at", "archived_at"] = "name",
    order: Literal["asc", "desc"] = "asc",
) -> UserListResponse:
    users, total = await create_queries(session_factory).list(
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
        items=[user_response(user) for user in users], total=total, page=page, page_size=page_size
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.READ))],
    session_factory: SessionFactoryDep,
) -> UserResponse:
    user = await create_queries(session_factory).get(user_id)
    if user is None:
        raise UserNotFoundError
    return user_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.CREATE))],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> UserResponse:
    user = await create_user_command(session_factory, identities).execute(
        actor=principal,
        name=payload.name,
        role=payload.role,
        login=payload.login,
        password=payload.password,
        active=payload.active,
    )
    return user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.UPDATE))],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> UserResponse:
    user = await update_user_command(session_factory, identities).execute(
        actor=principal, user_id=user_id, login=payload.login, name=payload.name, role=payload.role
    )
    return user_response(user)


@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    user_id: UUID,
    payload: UpdatePasswordRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(UserPermission.SET_PASSWORD))
    ],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> None:
    await set_password_command(session_factory, identities).execute(
        actor=principal, user_id=user_id, password=payload.password
    )


@router.put("/{user_id}/active", response_model=UserResponse)
async def update_active(
    user_id: UUID,
    payload: UpdateActiveRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(UserPermission.SET_ACTIVE))
    ],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> UserResponse:
    return user_response(
        await set_active_command(session_factory, identities).execute(
            actor=principal, user_id=user_id, active=payload.active
        )
    )


@router.put("/{user_id}/archived", response_model=UserResponse)
async def update_archived(
    user_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.ARCHIVE))],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> UserResponse:
    return user_response(
        await set_archived_command(session_factory, identities).execute(
            actor=principal, user_id=user_id, archived=payload.archived
        )
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.DELETE))],
    session_factory: SessionFactoryDep,
    identities: IdentityProviderDep,
) -> None:
    await delete_user_command(session_factory, identities).execute(actor=principal, user_id=user_id)
