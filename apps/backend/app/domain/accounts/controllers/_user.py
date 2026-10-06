"""User Account Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, Request, delete, get, patch, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.audit import USER_AUDIT_FIELDS
from app.domain.accounts.events import UserChanged
from app.domain.accounts.permissions import UserPermission
from app.domain.accounts.schemas import (
    User,
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserUpdate,
)
from app.domain.accounts.services import UserService
from app.domain.audit.changes import ChangeRecorder
from app.lib.audit import change_details, snapshot
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import create_active_filter_provider, provide_archived_filter
from app.lib.kratos import KratosClient
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service import OffsetPagination

UserId = Annotated[UUID, Parameter(title="User ID", description="The user to act on.")]


class UserController(Controller):
    """User Account Controller."""

    path = "/users"
    tags = ["User Accounts"]  # noqa: RUF012

    dependencies = create_service_dependencies(
        UserService,
        key="users_service",
        filters={
            "id_filter": UUID,
            "search": "name,identity_login",
            "pagination_type": "limit_offset",
            "pagination_size": 25,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
            "in_fields": [FieldNameType(name="role", type_hint=UserRole)],
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["active_filter"] = Provide(create_active_filter_provider("identity_active"), sync_to_thread=False)

    @get(
        operation_id="ListUsers",
        guards=[requires_permission(UserPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_users(
        self,
        users_service: NamedDependency[UserService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
        active_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[User]:
        results, total = await users_service.get_many_and_count(*filters, *archived_filter, *active_filter)

        return users_service.to_schema(
            results,
            total,
            filters,
            schema_type=User,
        )

    @get(
        operation_id="GetUser",
        path="/{user_id:uuid}",
        guards=[requires_permission(UserPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_user(
        self,
        users_service: NamedDependency[UserService],
        user_id: UserId,
    ) -> User:
        db_obj = await users_service.get(user_id)

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @post(
        operation_id="CreateUser",
        guards=[
            requires_permission(UserPermission.CREATE),
            requires_permission(UserPermission.ASSIGN_ROLE),
        ],
        responses=error_responses(401, 403, 409, 503),
    )
    async def create_user(
        self,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        data: UserCreate,
    ) -> User:
        db_obj = await users_service.create_user(
            data,
            kratos=kratos,
            uow=uow,
        )
        await changes.record(
            "user.created",
            db_obj,
            event=UserChanged(user_id=db_obj.id),
            details={"role": data.role.value, "is_active": data.is_active},
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @patch(
        operation_id="UpdateUser",
        path="/{user_id:uuid}",
        guards=[requires_permission(UserPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409, 503),
    )
    async def update_user(
        self,
        data: UserUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        before = snapshot(await users_service.get(user_id), USER_AUDIT_FIELDS)
        db_obj = await users_service.update_user(
            user_id,
            data,
            kratos=kratos,
            uow=uow,
        )

        if details := change_details(before, snapshot(db_obj, USER_AUDIT_FIELDS)):
            await changes.record(
                "user.updated",
                db_obj,
                event=UserChanged(user_id=db_obj.id),
                details=details,
            )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @put(
        operation_id="UpdateUserRole",
        path="/{user_id:uuid}/role",
        guards=[requires_permission(UserPermission.ASSIGN_ROLE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_role(
        self,
        request: Request[m.User, Any, Any],
        data: UserRoleUpdate,
        users_service: NamedDependency[UserService],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        previous_role = (await users_service.get(user_id)).role
        db_obj = await users_service.assign_role(
            user_id,
            data.role,
            actor_id=request.user.id,
            expected_updated_at=data.expected_updated_at,
        )

        if previous_role != data.role:
            await changes.record(
                "user.role_changed",
                db_obj,
                event=UserChanged(user_id=db_obj.id),
                details=change_details({"role": previous_role.value}, {"role": data.role.value}),
            )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @put(
        operation_id="UpdateUserPassword",
        path="/{user_id:uuid}/password",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(UserPermission.SET_PASSWORD)],
        responses=error_responses(401, 403, 404, 409, 503),
    )
    async def update_password(
        self,
        data: UserPasswordUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> None:
        target = await users_service.set_password(
            user_id,
            data.password,
            kratos=kratos,
        )

        await changes.record("user.password_changed", target, event=UserChanged(user_id=target.id))

    @post(
        operation_id="ActivateUser",
        path="/{user_id:uuid}/activate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(UserPermission.SET_ACTIVE)],
        responses=error_responses(401, 403, 404, 409, 503),
    )
    async def activate_user(
        self,
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        return await self._set_active(
            request,
            users_service,
            kratos,
            uow,
            changes,
            user_id,
            is_active=True,
        )

    @post(
        operation_id="DeactivateUser",
        path="/{user_id:uuid}/deactivate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(UserPermission.SET_ACTIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def deactivate_user(
        self,
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        return await self._set_active(
            request,
            users_service,
            kratos,
            uow,
            changes,
            user_id,
            is_active=False,
        )

    @staticmethod
    async def _set_active(
        request: Request[m.User, Any, Any],
        users_service: UserService,
        kratos: KratosClient,
        uow: UnitOfWork,
        changes: ChangeRecorder,
        user_id: UUID,
        *,
        is_active: bool,
    ) -> User:
        was_active = (await users_service.get(user_id)).identity_active
        db_obj = await users_service.set_active(
            user_id,
            is_active=is_active,
            kratos=kratos,
            uow=uow,
            actor_id=request.user.id,
        )

        if was_active != is_active:
            await changes.record(
                "user.activated" if is_active else "user.deactivated",
                db_obj,
                event=UserChanged(user_id=db_obj.id),
            )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @post(
        operation_id="ArchiveUser",
        path="/{user_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(UserPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def archive_user(
        self,
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        return await self._set_archived(
            request,
            users_service,
            kratos,
            uow,
            changes,
            user_id,
            archived=True,
        )

    @post(
        operation_id="RestoreUser",
        path="/{user_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(UserPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_user(
        self,
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> User:
        return await self._set_archived(
            request,
            users_service,
            kratos,
            uow,
            changes,
            user_id,
            archived=False,
        )

    @staticmethod
    async def _set_archived(
        request: Request[m.User, Any, Any],
        users_service: UserService,
        kratos: KratosClient,
        uow: UnitOfWork,
        changes: ChangeRecorder,
        user_id: UUID,
        *,
        archived: bool,
    ) -> User:
        was_archived = (await users_service.get(user_id)).archived_at is not None
        db_obj = await users_service.set_archived(
            user_id,
            archived=archived,
            kratos=kratos,
            uow=uow,
            actor_id=request.user.id,
        )

        if was_archived != archived:
            await changes.record(
                "user.archived" if archived else "user.restored",
                db_obj,
                event=UserChanged(user_id=db_obj.id),
            )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @delete(
        operation_id="DeleteUser",
        path="/{user_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(UserPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_user(
        self,
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        user_id: UserId,
    ) -> None:
        target = await users_service.delete_user(
            user_id,
            kratos=kratos,
            uow=uow,
            actor_id=request.user.id,
        )

        await changes.record("user.deleted", target, event=UserChanged(user_id=target.id))
