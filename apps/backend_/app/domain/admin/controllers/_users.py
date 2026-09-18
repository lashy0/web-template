"""Admin Users Controller."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from litestar import Controller, put
from litestar.di import NamedDependency
from litestar.params import Parameter
from litestar.status_codes import HTTP_204_NO_CONTENT

from app.domain.accounts.guards import requires_administrator
from app.domain.accounts.schemas import (
    User,
    UserActiveUpdate,
    UserArchivedUpdate,
    UserPasswordUpdate,
)
from app.domain.accounts.services import UserService
from app.lib.deps import create_service_dependencies
from app.lib.kratos import KratosClient


class AdminUsersController(Controller):
    """Admin user management endpoints."""

    path = "/admin/users"
    tags = ["Admin"]
    guards = [requires_administrator]

    dependencies = create_service_dependencies(
        UserService,
        key="users_service",
        error_messages={
            "duplicate_key": "User already exists.",
            "integrity": "User operation failed.",
        },
    )

    @put(
        operation_id="AdminUpdateUserPassword",
        path="/{user_id:uuid}/password",
        status_code=HTTP_204_NO_CONTENT,
    )
    async def update_password(
        self,
        data: UserPasswordUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user whose password to update.",
            ),
        ],
    ) -> None:
        await users_service.set_password(
            user_id,
            data.password,
            kratos=kratos,
        )

    @put(
        operation_id="AdminUpdateUserActive",
        path="/{user_id:uuid}/active",
    )
    async def update_active(
        self,
        data: UserActiveUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user to activate or deactivate.",
            ),
        ],
    ) -> User:
        db_obj = await users_service.set_active(
            user_id,
            is_active=data.is_active,
            kratos=kratos,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @put(
        operation_id="AdminUpdateUserArchived",
        path="/{user_id:uuid}/archived",
    )
    async def update_archived(
        self,
        data: UserArchivedUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user to archive or restore.",
            ),
        ],
    ) -> User:
        db_obj = await users_service.set_archived(
            user_id,
            archived=data.archived,
            kratos=kratos,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )
