"""The production application is composed with the production permission policy."""

from __future__ import annotations

import pytest

from app.lib.authorization import PermissionPolicy
from app.lib.authorization.guards import AUTHORIZATION_POLICY_STATE_KEY
from app.server.asgi import create_app
from app.server.authorization import create_authorization_policy

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_production_app_installs_the_production_policy() -> None:
    policy = create_app().state[AUTHORIZATION_POLICY_STATE_KEY]

    assert isinstance(policy, PermissionPolicy)
    assert policy.grants == create_authorization_policy().grants
