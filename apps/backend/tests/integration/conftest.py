from __future__ import annotations

from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar.testing import AsyncTestClient

from app.config import Settings, get_settings
from app.db import models as m
from app.db.enums import UserRole
from app.lib.hydra import HydraClient
from app.lib.kratos import KratosClient
from app.lib.kratos.exceptions import KratosInvalidSessionError
from app.lib.kratos.schemas import KratosIdentity
from app.lib.uow import unit_of_work
from app.server.asgi import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.conftest import HydraService, KratosService


pytestmark = pytest.mark.anyio


class FakeSessionVerifier:
    """Stands in for the Kratos Public API check of browser sessions.

    Only the Kratos boundary is replaced: the middleware still loads the local
    user from PostgreSQL and the guards still apply the production policy.
    """

    def __init__(self, cookie_name: str) -> None:
        self._cookie_name = cookie_name
        self._identities: dict[str, KratosIdentity] = {}

    def sign_in(self, user: m.User) -> str:
        """Open a session for ``user`` and return its cookie value."""
        token = uuid4().hex
        self._identities[token] = KratosIdentity(
            id=user.identity_id,
            login=user.identity_login,
            is_active=True,
        )

        return token

    async def verify_session(self, *, cookie_header: str) -> KratosIdentity:
        morsel = SimpleCookie(cookie_header).get(self._cookie_name)
        identity = self._identities.get(morsel.value) if morsel is not None else None

        if identity is None:
            raise KratosInvalidSessionError(detail="Unknown session")

        return identity


class SignIn(Protocol):
    async def __call__(self, role: UserRole = ...) -> m.User: ...


@pytest.fixture(name="kratos_client")
def fx_kratos_client(kratos_service: KratosService) -> KratosClient:
    """Kratos Admin API client bound to the isolated test instance."""
    return KratosClient(base_url=kratos_service.admin_url)


@pytest.fixture(name="hydra_client")
def fx_hydra_client(hydra_service: HydraService) -> HydraClient:
    """Hydra Admin API client bound to the isolated test instance."""
    return HydraClient(base_url=hydra_service.admin_url)


@pytest.fixture(name="settings")
def fx_settings(
    db_schema: None,
    kratos_service: KratosService,
    hydra_service: HydraService,
) -> Settings:
    """Settings pointing at the test PostgreSQL, Kratos and Hydra."""
    return get_settings()


@pytest.fixture(name="session_verifier")
def fx_session_verifier(settings: Settings) -> FakeSessionVerifier:
    return FakeSessionVerifier(settings.kratos.session_cookie)


@pytest.fixture(name="app")
def fx_app(settings: Settings, session_verifier: FakeSessionVerifier) -> Litestar:
    """Application built from the test settings, with sessions opened by ``sign_in``."""
    return create_app(settings=settings, session_verifier=session_verifier)


@pytest.fixture(name="client")
async def fx_client(app: Litestar, db_cleanup: None) -> AsyncIterator[AsyncTestClient[Litestar]]:
    """HTTP client running the application lifespan; requests are anonymous until ``sign_in``."""
    async with AsyncTestClient(app) as client:
        yield client

    # Advanced Alchemy 1.11 renames the engine state key of every config after
    # the first in a process, and its lifespan then skips ``dispose()``. Without
    # this, each application of the test process keeps pooled connections open
    # until the test database runs out of them.
    for config in app.plugins.get(SQLAlchemyPlugin).config:
        if isinstance(config, SQLAlchemyAsyncConfig):
            await config.get_engine().dispose()


@pytest.fixture(name="sign_in")
def fx_sign_in(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    session_verifier: FakeSessionVerifier,
    settings: Settings,
) -> SignIn:
    """Return a helper that commits a local user with ``role`` and signs the client in as them.

    The user has no Kratos identity: routes that change the signed-in user in
    Kratos need a user created through ``UserService`` instead.
    """

    async def _sign_in(role: UserRole = UserRole.ADMINISTRATOR) -> m.User:
        user = m.User(
            identity_id=uuid4(),
            identity_login=f"actor-{uuid4().hex[:8]}",
            identity_active=True,
            name="Test Actor",
            role=role,
        )

        async with unit_of_work(session):
            session.add(user)

        client.cookies.set(settings.kratos.session_cookie, session_verifier.sign_in(user))

        return user

    return _sign_in
