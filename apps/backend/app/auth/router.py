from typing import cast

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep
from app.contexts.identity.users.exceptions import UserNotFoundError
from app.contexts.identity.users.presentation import user_response
from app.contexts.identity.users.queries import UserQueries
from app.contexts.identity.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def me(principal: CurrentPrincipalDep, request: Request) -> UserResponse:
    session_factory = request.app.state.database.session_factory
    user = await UserQueries(cast(async_sessionmaker[AsyncSession], session_factory)).get(
        principal.user_id
    )
    if user is None:
        raise UserNotFoundError
    return user_response(user)
