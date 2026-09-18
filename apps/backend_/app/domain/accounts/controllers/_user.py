"""User Account Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_204_NO_CONTENT

from app.domain.accounts.guards import requires_administrator
from app.domain.accounts.schemas import User, UserCreate, UserUpdate
from app.domain.accounts.services import UserService
from app.lib.deps import create_service_dependencies
from app.lib.kratos import KratosClient

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service import OffsetPagination


class UserController(Controller):
    """User Account Controller."""

    path = "/users"
    tags = ["User Accounts"]
    guards = [requires_administrator]

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

    @get(operation_id="ListUsers")
    async def list_users(
        self,
        users_service: NamedDependency[UserService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[User]:
        results, total = await users_service.list_and_count(*filters)

        return users_service.to_schema(
            results,
            total,
            filters,
            schema_type=User,
        )

    @get(
        operation_id="GetUser",
        path="/{user_id:uuid}",
    )
    async def get_user(
        self,
        users_service: NamedDependency[UserService],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user to retrieve.",
            ),
        ],
    ) -> User:
        db_obj = await users_service.get(user_id)

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @post(operation_id="CreateUser")
    async def create_user(
        self,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        data: UserCreate,
    ) -> User:
        db_obj = await users_service.create_user(
            data,
            kratos=kratos,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @patch(
        operation_id="UpdateUser",
        path="/{user_id:uuid}",
    )
    async def update_user(
        self,
        data: UserUpdate,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user to update.",
            ),
        ],
    ) -> User:
        db_obj = await users_service.update_user(
            user_id,
            data,
            kratos=kratos,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )

    @delete(
        operation_id="DeleteUser",
        path="/{user_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
    )
    async def delete_user(
        self,
        users_service: NamedDependency[UserService],
        kratos: NamedDependency[KratosClient],
        user_id: Annotated[
            UUID,
            Parameter(
                title="User ID",
                description="The user to delete.",
            ),
        ],
    ) -> None:
        await users_service.delete_user(
            user_id,
            kratos=kratos,
        )
