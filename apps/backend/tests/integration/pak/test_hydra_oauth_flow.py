from uuid import uuid4

import pytest
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.exceptions import ForbiddenError, OAuthClientNotFoundError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.core.config import Settings
from app.infrastructure.hydra.client import HydraOAuthClientManager, HydraTokenIntrospector
from app.modules.pak.models import PakDeviceKind
from app.modules.pak.service import PakManagementService


def _administrator() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=Role.ADMINISTRATOR,
    )


async def _token(
    settings: Settings,
    *,
    client_id: str,
    client_secret: str,
) -> str:
    async with AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        timeout=settings.HYDRA_PUBLIC_TIMEOUT,
    ) as client:
        token = await client.fetch_token(
            f"{settings.HYDRA_PUBLIC_URL.rstrip('/')}/oauth2/token",
            grant_type="client_credentials",
        )

    return str(token["access_token"])


@pytest.mark.integration
async def test_pak_oauth_credentials_are_managed_by_hydra_end_to_end(
    database_session_factory: async_sessionmaker[AsyncSession],
    test_settings: Settings,
) -> None:
    """Exercise the direct PAK -> Hydra -> backend authorization boundary."""
    manager = HydraOAuthClientManager(test_settings)
    introspector = HydraTokenIntrospector(test_settings)
    service = PakManagementService(
        database_session_factory,
        manager,
        introspector,
        SecretStr(Fernet.generate_key().decode("ascii")),
    )
    actor = _administrator()
    pak = None

    try:
        pak, client_secret = await service.create(
            actor=actor,
            code=f"PAK-HYDRA-{uuid4().hex[:12]}",
            kind=PakDeviceKind.OTK_LINE,
            active=True,
        )

        # PAK exchanges its credentials with Hydra directly. The backend does
        # not receive the secret during token acquisition.
        access_token = await _token(
            test_settings,
            client_id=pak.oauth_client_id,
            client_secret=client_secret,
        )
        introspection = await introspector.introspect_access_token(access_token)
        assert introspection.active is True
        assert introspection.client_id == pak.oauth_client_id

        # This is the dependency used by PAK business endpoints.
        assert (await service.authorize_machine_access_token(access_token)).id == pak.id

        with pytest.raises(OAuth2Error):
            await _token(
                test_settings,
                client_id=pak.oauth_client_id,
                client_secret="incorrect-client-secret",
            )

        await service.set_active(actor=actor, pak_id=pak.id, active=False)
        with pytest.raises(ForbiddenError):
            await service.authorize_machine_access_token(access_token)

        await service.set_active(actor=actor, pak_id=pak.id, active=True)
        await service.set_archived(actor=actor, pak_id=pak.id, archived=True)
        with pytest.raises(ForbiddenError):
            await service.authorize_machine_access_token(access_token)
        await service.set_archived(actor=actor, pak_id=pak.id, archived=False)
        await service.set_active(actor=actor, pak_id=pak.id, active=True)

        rotated_secret = await service.rotate_access_key(actor=actor, pak_id=pak.id)
        assert await service.get_access_key(actor=actor, pak_id=pak.id) == rotated_secret

        with pytest.raises(OAuth2Error):
            await _token(
                test_settings,
                client_id=pak.oauth_client_id,
                client_secret=client_secret,
            )

        rotated_token = await _token(
            test_settings,
            client_id=pak.oauth_client_id,
            client_secret=rotated_secret,
        )
        assert (await service.authorize_machine_access_token(rotated_token)).id == pak.id

        await service.delete(actor=actor, pak_id=pak.id)
        with pytest.raises(OAuth2Error):
            await _token(
                test_settings,
                client_id=pak.oauth_client_id,
                client_secret=rotated_secret,
            )
        pak = None
    finally:
        if pak is not None:
            try:
                await manager.delete_client(pak.oauth_client_id)
            except OAuthClientNotFoundError:
                pass
