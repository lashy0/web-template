import pytest
from litestar.testing import AsyncTestClient

from app.domain.accounts.permissions import UserPermission
from app.server.asgi import create_app
from tests.unit.route_permissions import assert_routes_require

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_user_routes_require_permissions() -> None:
    assert_routes_require(
        {
            "ListUsers": {UserPermission.READ},
            "GetUser": {UserPermission.READ},
            # Creating a user chooses its role.
            "CreateUser": {UserPermission.CREATE, UserPermission.ASSIGN_ROLE},
            "UpdateUser": {UserPermission.UPDATE},
            "UpdateUserRole": {UserPermission.ASSIGN_ROLE},
            "UpdateUserPassword": {UserPermission.SET_PASSWORD},
            "ActivateUser": {UserPermission.SET_ACTIVE},
            "DeactivateUser": {UserPermission.SET_ACTIVE},
            "ArchiveUser": {UserPermission.ARCHIVE},
            "RestoreUser": {UserPermission.ARCHIVE},
            "DeleteUser": {UserPermission.DELETE},
        }
    )


@pytest.mark.anyio
async def test_account_routes_require_authentication() -> None:
    async with AsyncTestClient(create_app()) as client:
        assert (await client.get("/users")).status_code == 401
        assert (await client.get("/auth/me")).status_code == 401
