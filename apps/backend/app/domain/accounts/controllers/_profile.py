"""User Profile Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, get, patch
from litestar.di import NamedDependency, Provide

from app.domain.accounts.audit import USER_AUDIT_FIELDS
from app.domain.accounts.deps import provide_current_user, provide_users_service
from app.domain.accounts.events import UserChanged
from app.domain.accounts.schemas import ProfileUpdate, User
from app.domain.accounts.services import UserService
from app.domain.audit.changes import ChangeRecorder
from app.lib.audit import change_details, snapshot
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from app.db import models as m


class ProfileController(Controller):
    """Current user profile."""

    path = "/auth"
    tags = ["Profile"]  # noqa: RUF012
    dependencies = {  # noqa: RUF012
        "current_user": Provide(provide_current_user, sync_to_thread=False),
        "users_service": Provide(provide_users_service),
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
        current_user: NamedDependency[m.User],
        data: ProfileUpdate,
        users_service: NamedDependency[UserService],
        changes: NamedDependency[ChangeRecorder],
    ) -> User:
        before = snapshot(current_user, USER_AUDIT_FIELDS)
        db_obj = await users_service.update_profile(
            current_user.id,
            data,
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
