from fastapi import APIRouter

from app.domains.identity.users.exceptions import UserNotFoundError
from app.domains.identity.users.presentation import user_response
from app.domains.identity.users.schemas import UserResponse
from app.domains.identity.users.wiring import create_queries
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def me(principal: CurrentPrincipalDep, session_factory: SessionFactoryDep) -> UserResponse:
    user = await create_queries(session_factory).get(principal.user_id)
    if user is None:
        raise UserNotFoundError
    return user_response(user)
