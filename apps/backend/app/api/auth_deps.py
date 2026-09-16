from typing import Annotated, cast

from fastapi import Depends, Request

from app.api.deps import DatabaseDep
from app.auth.contracts import SessionVerifier
from app.auth.exceptions import AccountDisabledError, InvalidSessionError, UserNotProvisionedError
from app.domains.identity.users.repository import UserRepository
from app.shared.security import CurrentPrincipal


async def get_session_verifier(request: Request) -> SessionVerifier:
    try:
        return cast(SessionVerifier, request.app.state.session_verifier)
    except AttributeError as exc:
        raise RuntimeError("Session verifier is not initialized") from exc


SessionVerifierDep = Annotated[SessionVerifier, Depends(get_session_verifier)]


async def get_current_principal(
    request: Request, database: DatabaseDep, verifier: SessionVerifierDep
) -> CurrentPrincipal:
    cookie = request.cookies.get(request.app.state.settings.KRATOS_SESSION_COOKIE)
    if not cookie:
        raise InvalidSessionError
    session = await verifier.verify_session(
        cookie_header=f"{request.app.state.settings.KRATOS_SESSION_COOKIE}={cookie}"
    )
    if not session.identity.active:
        raise AccountDisabledError
    async with database.session_factory() as db_session:
        user = await UserRepository(db_session).get_by_identity_id(session.identity.id)
    if user is None:
        raise UserNotProvisionedError

    return CurrentPrincipal(
        user_id=user.id,
        identity_id=session.identity.id,
        session_id=session.id,
        role=user.role,
        name=user.name,
        login=user.identity_login,
    )
