from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.pak.exceptions import InvalidMachineAccessTokenError
from app.modules.pak.models import PakDevice
from app.modules.pak.service import PakManagementService


_bearer = HTTPBearer(
    auto_error=False,
)


async def get_current_pak(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
) -> PakDevice:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
    ):
        raise InvalidMachineAccessTokenError

    service = cast(PakManagementService, request.app.state.pak_management)

    return await service.authorize_machine_access_token(credentials.credentials)


CurrentPakDep = Annotated[
    PakDevice,
    Depends(get_current_pak),
]
