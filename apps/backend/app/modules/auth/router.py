from typing import cast

from fastapi import APIRouter, Request

from app.api.auth_deps import CurrentPrincipalDep
from app.modules.users.router import _response
from app.modules.users.schemas import UserResponse
from app.modules.users.service import UserManagementService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def me(principal: CurrentPrincipalDep, request: Request) -> UserResponse:
    service = cast(UserManagementService, request.app.state.user_management)
    user = await service.get(principal.user_id)
    assert user is not None
    return _response(user)
