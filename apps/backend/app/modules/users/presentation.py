from typing import cast

from .enums import AuthState
from .models import User
from .schemas import UserResponse
from .services.bootstrap import BOOTSTRAP_ADMIN_USER_ID


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        is_system=user.id == BOOTSTRAP_ADMIN_USER_ID,
        identity_id=user.identity_id,
        name=user.name,
        role=user.role,
        login=user.identity_login,
        auth_state=cast(AuthState, user.auth_state),
        auth_state_synced_at=user.auth_state_synced_at,
        archived_at=user.archived_at,
    )
