from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.permissions import UserPermission
from app.lib.authorization import granted_permissions, requires_permission
from app.lib.authorization.guards import AUTHORIZATION_POLICY_STATE_KEY
from app.server.authorization import create_authorization_policy

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def _connection(user: m.User | None) -> MagicMock:
    connection = MagicMock()
    connection.scope = {} if user is None else {"user": user}
    connection.app.state = {
        AUTHORIZATION_POLICY_STATE_KEY: create_authorization_policy(),
    }

    return connection


def _user(role: UserRole) -> m.User:
    return m.User(
        identity_id=uuid4(),
        identity_login="guard-user",
        name="Guard User",
        role=role,
    )


def test_user_with_permission_passes() -> None:
    requires_permission(UserPermission.READ)(_connection(_user(UserRole.ADMINISTRATOR)), MagicMock())


def test_user_without_permission_is_forbidden() -> None:
    with pytest.raises(PermissionDeniedException):
        requires_permission(UserPermission.READ)(_connection(_user(UserRole.OPERATOR)), MagicMock())


def test_anonymous_user_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        requires_permission(UserPermission.READ)(_connection(None), MagicMock())


def test_granted_permissions_are_those_of_the_role() -> None:
    connection = _connection(_user(UserRole.ENGINEER))
    connection.user = connection.scope["user"]

    assert granted_permissions(connection) == create_authorization_policy().permissions_for_role(UserRole.ENGINEER)
