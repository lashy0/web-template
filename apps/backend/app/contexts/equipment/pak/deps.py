from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .authentication import PakMachineAuthenticator
from .exceptions import InvalidMachineAccessTokenError
from .model import PakDevice

_bearer = HTTPBearer(auto_error=False)


async def get_current_pak(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> PakDevice:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise InvalidMachineAccessTokenError
    authenticator = cast(PakMachineAuthenticator, request.app.state.pak_machine_authenticator)
    return await authenticator.authorize_machine_access_token(credentials.credentials)


CurrentPakDep = Annotated[PakDevice, Depends(get_current_pak)]
