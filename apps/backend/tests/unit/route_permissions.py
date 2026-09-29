"""Check which permissions the production routes require, through their guards."""

from collections.abc import Mapping
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from litestar.exceptions import PermissionDeniedException

from app.db import models as m
from app.db.enums import UserRole
from app.lib.authorization import PermissionPolicy
from app.lib.authorization.guards import AUTHORIZATION_POLICY_STATE_KEY
from app.server.asgi import create_app


def _run_guards(operation_id: str, granted: set[str]) -> None:
    handler = next(
        handler
        for route in create_app().routes
        for handler in getattr(route, "route_handlers", ())
        if handler.operation_id == operation_id
    )
    connection = MagicMock()
    connection.scope = {
        "user": m.User(
            identity_id=uuid4(),
            identity_login="route-user",
            name="Route User",
            role=UserRole.MANAGER,
        )
    }
    connection.app.state = {AUTHORIZATION_POLICY_STATE_KEY: PermissionPolicy({UserRole.MANAGER: granted})}

    for guard in handler.guards or ():
        guard(connection, handler)


def assert_routes_require(expected: Mapping[str, set[str]]) -> None:
    """Each operation passes with its permissions and fails without them."""
    for operation_id, required in expected.items():
        _run_guards(operation_id, required)

        with pytest.raises(PermissionDeniedException):
            _run_guards(operation_id, set())
