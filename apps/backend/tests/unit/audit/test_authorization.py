import pytest

from app.db.enums import UserRole
from app.domain.audit.permissions import AuditPermission
from app.server.authorization import create_authorization_policy
from tests.unit.route_permissions import assert_routes_require

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_audit_routes_require_audit_read() -> None:
    assert_routes_require({"ListAuditEntries": {AuditPermission.READ}})


@pytest.mark.parametrize("role", list(UserRole))
def test_only_administrators_read_the_audit_log(role: UserRole) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert (AuditPermission.READ in permissions) is (role is UserRole.ADMINISTRATOR)
