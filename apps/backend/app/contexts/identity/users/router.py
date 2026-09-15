from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.shared.security import Role

from .commands import (
    CreateUser,
    DeleteUser,
    SetUserActive,
    SetUserArchived,
    SetUserPassword,
    UpdateUser,
)
from .enums import AuthState
from .exceptions import UserNotFoundError
from .permissions import UserPermission
from .presentation import user_response
from .queries import UserQueries
from .schemas import (
    CreateUserRequest,
    UpdateActiveRequest,
    UpdateArchivedRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _component(request: Request, name: str, _component_type: type[object]) -> object:
    return cast(object, getattr(request.app.state, name))


@router.get("", response_model=UserListResponse)
async def list_users(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.READ))],
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
    users, total = await cast(UserQueries, _component(request, "user_queries", UserQueries)).list(
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
    request: Request,
) -> UserResponse:
    user = await cast(UserQueries, _component(request, "user_queries", UserQueries)).get(user_id)
    if user is None:
        raise UserNotFoundError
    return user_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.CREATE))],
    request: Request,
) -> UserResponse:
    user = await cast(CreateUser, _component(request, "create_user", CreateUser)).execute(
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
    request: Request,
) -> UserResponse:
    user = await cast(UpdateUser, _component(request, "update_user", UpdateUser)).execute(
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
    request: Request,
) -> None:
    await cast(SetUserPassword, _component(request, "set_user_password", SetUserPassword)).execute(
        actor=principal, user_id=user_id, password=payload.password
    )


@router.put("/{user_id}/active", response_model=UserResponse)
async def update_active(
    user_id: UUID,
    payload: UpdateActiveRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(UserPermission.SET_ACTIVE))
    ],
    request: Request,
) -> UserResponse:
    return user_response(
        await cast(SetUserActive, _component(request, "set_user_active", SetUserActive)).execute(
            actor=principal, user_id=user_id, active=payload.active
        )
    )


@router.put("/{user_id}/archived", response_model=UserResponse)
async def update_archived(
    user_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.ARCHIVE))],
    request: Request,
) -> UserResponse:
    return user_response(
        await cast(
            SetUserArchived, _component(request, "set_user_archived", SetUserArchived)
        ).execute(actor=principal, user_id=user_id, archived=payload.archived)
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(UserPermission.DELETE))],
    request: Request,
) -> None:
    await cast(DeleteUser, _component(request, "delete_user", DeleteUser)).execute(
        actor=principal, user_id=user_id
    )
