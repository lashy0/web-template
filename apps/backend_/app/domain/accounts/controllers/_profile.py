"""User Profile Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, get, patch

from app.domain.accounts.schemas import ProfileUpdate, User
from app.domain.accounts.services import UserService

if TYPE_CHECKING:
    from app.db import models as m


class ProfileController(Controller):
    """Current user profile."""

    path = "/me"
    tags = ["Profile"]

    @get(
        operation_id="GetProfile",
        summary="Get current user profile",
    )
    async def get_profile(
        self,
        current_user: m.User,
        users_service: UserService,
    ) -> User:
        return users_service.to_schema(
            current_user,
            schema_type=User,
        )

    @patch(
        operation_id="UpdateProfile",
        summary="Update current user profile",
    )
    async def update_profile(
        self,
        current_user: m.User,
        data: ProfileUpdate,
        users_service: UserService,
    ) -> User:
        db_obj = await users_service.update_profile(
            current_user.id,
            data,
        )

        return users_service.to_schema(
            db_obj,
            schema_type=User,
        )
