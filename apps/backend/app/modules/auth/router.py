from typing import cast

from fastapi import APIRouter, Request

from app.api.auth_deps import CurrentPrincipalDep
from app.modules.users.exceptions import UserNotFoundError
from app.modules.users.presentation import user_response
from app.modules.users.schemas import UserResponse
from app.modules.users.services import UserManagementService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def me(principal: CurrentPrincipalDep, request: Request) -> UserResponse:
    service = cast(UserManagementService, request.app.state.user_management)
    user = await service.get(principal.user_id)

    if user is None:
        raise UserNotFoundError

    return user_response(user)
