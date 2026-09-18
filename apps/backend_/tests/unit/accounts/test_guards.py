from __future__ import annotations

from unittest.mock import Mock

import pytest
from litestar.exceptions import PermissionDeniedException

from app.db.enums import UserRole
from app.domain.accounts.guards import requires_administrator

pytestmark = [pytest.mark.anyio, pytest.mark.unit, pytest.mark.auth, pytest.mark.security]


def test_administrator_passes() -> None:
    """An administrator may access protected routes."""
    user = Mock()
    user.role = UserRole.ADMINISTRATOR
    connection = Mock()
    connection.user = user

    requires_administrator(connection, Mock())


def test_non_administrator_raises_permission_denied() -> None:
    """A non-administrator is rejected by the guard."""
    user = Mock()
    user.role = UserRole.OPERATOR
    connection = Mock()
    connection.user = user

    with pytest.raises(PermissionDeniedException, match="Administrator access required"):
        requires_administrator(connection, Mock())
