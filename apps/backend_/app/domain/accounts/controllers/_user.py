"""User Account Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from litestar import Controller, Request, delete, get, patch, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.accounts.permissions import UserPermission
from app.domain.accounts.schemas import (
    User,
    UserCreate,
    UserPasswordUpdate,
    UserRoleUpdate,
    UserUpdate,
)
from app.domain.accounts.services import UserService
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
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
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_user_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.User,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Write an audit entry from the request-scoped controller context."""
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="user",
            target_id=str(target.id),
            target_label=target.identity_login,
            details=details,
            request=request,
        )

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
    ) -> OffsetPagination[User]:
        results, total = await users_service.get_many_and_count(*filters, *archived_filter)

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
        request: Request[m.User, Any, Any],
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        data: UserCreate,
    ) -> User:
        db_obj = await users_service.create_user(
            data,
            kratos=kratos,
            uow=uow,
        )
        await self._log_user_action(
            request,
            audit_service,
            action="user.created",
            target=db_obj,
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
        request: Request[m.User, Any, Any],
        data: UserUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> User:
        db_obj = await users_service.update_user(
            user_id,
            data,
            kratos=kratos,
            uow=uow,
        )

        await self._log_user_action(
            request,
            audit_service,
            action="user.updated",
            target=db_obj,
            details={"fields": [field for field in ("login", "name") if getattr(data, field) is not msgspec.UNSET]},
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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        user_id: UserId,
    ) -> User:
        previous_role = (await users_service.get(user_id)).role
        db_obj = await users_service.assign_role(
            user_id,
            data.role,
            actor_id=request.user.id,
        )

        if previous_role != data.role:
            await self._log_user_action(
                request,
                audit_service,
                action="user.role_changed",
                target=db_obj,
                details={"from": previous_role.value, "to": data.role.value},
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
        request: Request[m.User, Any, Any],
        data: UserPasswordUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the audit entry commits
        user_id: UserId,
    ) -> None:
        target = await users_service.set_password(
            user_id,
            data.password,
            kratos=kratos,
        )

        await self._log_user_action(
            request,
            audit_service,
            action="user.password_changed",
            target=target,
        )

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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> User:
        return await self._set_active(
            request,
            users_service,
            kratos,
            audit_service,
            uow,
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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> User:
        return await self._set_active(
            request,
            users_service,
            kratos,
            audit_service,
            uow,
            user_id,
            is_active=False,
        )

    async def _set_active(
        self,
        request: Request[m.User, Any, Any],
        users_service: UserService,
        kratos: KratosClient,
        audit_service: AuditLogService,
        uow: UnitOfWork,
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
            await self._log_user_action(
                request,
                audit_service,
                action="user.activated" if is_active else "user.deactivated",
                target=db_obj,
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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> User:
        return await self._set_archived(
            request,
            users_service,
            kratos,
            audit_service,
            uow,
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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> User:
        return await self._set_archived(
            request,
            users_service,
            kratos,
            audit_service,
            uow,
            user_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        users_service: UserService,
        kratos: KratosClient,
        audit_service: AuditLogService,
        uow: UnitOfWork,
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
            await self._log_user_action(
                request,
                audit_service,
                action="user.archived" if archived else "user.restored",
                target=db_obj,
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
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        user_id: UserId,
    ) -> None:
        target = await users_service.delete_user(
            user_id,
            kratos=kratos,
            uow=uow,
            actor_id=request.user.id,
        )

        await self._log_user_action(
            request,
            audit_service,
            action="user.deleted",
            target=target,
        )
