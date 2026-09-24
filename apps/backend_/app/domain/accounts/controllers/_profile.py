"""User Profile Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import msgspec
from litestar import Controller, Request, get, patch
from litestar.di import NamedDependency, Provide

from app.domain.accounts.deps import provide_current_user, provide_users_service
from app.domain.accounts.schemas import ProfileUpdate, User
from app.domain.accounts.services import UserService
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from app.db import models as m


class ProfileController(Controller):
    """Current user profile."""

    path = "/auth"
    tags = ["Profile"]  # noqa: RUF012
    dependencies = {  # noqa: RUF012
        "current_user": Provide(provide_current_user, sync_to_thread=False),
        "users_service": Provide(provide_users_service),
        "audit_service": Provide(provide_audit_log_service),
    }

    @get(
        operation_id="GetProfile",
        path="/me",
        summary="Get current user profile",
        description="User profile information.",
        responses=error_responses(401),
    )
    async def get_profile(
        self,
        current_user: NamedDependency[m.User],
        users_service: NamedDependency[UserService],
    ) -> User:
        """User profile.

        Returns:
            User: The current user's profile.
        """
        return users_service.to_schema(
            current_user,
            schema_type=User,
        )

    @patch(
        operation_id="UpdateProfile",
        path="/me",
        summary="Update current user profile",
        responses=error_responses(401, 409),
    )
    async def update_profile(
        self,
        request: Request[m.User, Any, Any],
        current_user: NamedDependency[m.User],
        data: ProfileUpdate,
        users_service: NamedDependency[UserService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
    ) -> User:
        db_obj = await users_service.update_profile(
            current_user.id,
            data,
        )
        await audit_service.log_action(
            action="user.updated",
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="user",
            target_id=str(db_obj.id),
            target_label=db_obj.identity_login,
            details={"fields": ["name"]} if data.name is not msgspec.UNSET else {"fields": []},
            request=request,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )
