from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from sqlalchemy.ext.asyncio import AsyncEngine

    from tests.conftest import HydraService, KratosService

pytestmark = pytest.mark.anyio


@pytest.fixture(name="app")
def fx_app(
    engine: AsyncEngine,
    db_schema: None,
    kratos_service: KratosService,
    hydra_service: HydraService,
) -> Litestar:
    """Create an application bound to the test database, Kratos and Hydra."""
    from app.server.asgi import create_app

    return create_app()


@pytest.fixture(name="raw_users")
def fx_raw_users() -> list[dict[str, Any]]:
    """Unstructured user representations."""

    from app.db.enums import UserRole

    return [
        {
            "login": "administrator",
            "password": "Administrator_2026!",
            "name": "Administrator",
            "role": UserRole.ADMINISTRATOR,
            "is_active": True,
            "archived": False,
        },
        {
            "login": "operator",
            "password": "OperatorPassword_2026!",
            "name": "Test Operator",
            "role": UserRole.OPERATOR,
            "is_active": True,
            "archived": False,
        },
        {
            "login": "archived-user",
            "password": "ArchivedPassword_2026!",
            "name": "Archived User",
            "role": UserRole.OPERATOR,
            "is_active": False,
            "archived": True,
        },
    ]
