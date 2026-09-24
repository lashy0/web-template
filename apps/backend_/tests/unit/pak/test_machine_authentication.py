from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar.exceptions import NotAuthorizedException

from app.domain.pak.deps import provide_current_pak
from app.lib.exceptions import AuthenticationError, AuthorizationError

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


async def test_valid_token_returns_pak() -> None:
    request = MagicMock(headers={"authorization": "Bearer token"})
    service = AsyncMock()

    pak = await provide_current_pak(request, service, MagicMock(), MagicMock())

    assert pak is service.authorize_machine_access_token.return_value


async def test_missing_token_is_unauthorized() -> None:
    request = MagicMock(headers={})
    service = AsyncMock()

    with pytest.raises(NotAuthorizedException):
        await provide_current_pak(request, service, MagicMock(), MagicMock())

    service.authorize_machine_access_token.assert_not_awaited()


async def test_invalid_token_is_unauthorized() -> None:
    request = MagicMock(headers={"authorization": "Bearer token"})
    service = AsyncMock()
    service.authorize_machine_access_token.side_effect = AuthenticationError("PAK access token is invalid.")

    with pytest.raises(NotAuthorizedException):
        await provide_current_pak(request, service, MagicMock(), MagicMock())


async def test_inactive_pak_is_forbidden() -> None:
    request = MagicMock(headers={"authorization": "Bearer token"})
    service = AsyncMock()
    service.authorize_machine_access_token.side_effect = AuthorizationError("PAK device is inactive or archived.")

    with pytest.raises(AuthorizationError):
        await provide_current_pak(request, service, MagicMock(), MagicMock())
