import pytest

from app.db.enums import UserRole
from app.domain.quality.permissions import DefectPermission, VerificationPermission
from app.server.authorization import create_authorization_policy
from tests.unit.route_permissions import assert_routes_require

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_defect_group_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListDefectGroups": {DefectPermission.READ},
            "GetDefectGroup": {DefectPermission.READ},
            "CreateDefectGroup": {DefectPermission.CREATE},
            "UpdateDefectGroup": {DefectPermission.UPDATE},
            "ArchiveDefectGroup": {DefectPermission.ARCHIVE},
            "RestoreDefectGroup": {DefectPermission.ARCHIVE},
            "DeleteDefectGroup": {DefectPermission.DELETE},
        }
    )


def test_defect_type_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListDefectTypes": {DefectPermission.READ},
            "GetDefectType": {DefectPermission.READ},
            "CreateDefectType": {DefectPermission.CREATE},
            "UpdateDefectType": {DefectPermission.UPDATE},
            "ArchiveDefectType": {DefectPermission.ARCHIVE},
            "RestoreDefectType": {DefectPermission.ARCHIVE},
            "DeleteDefectType": {DefectPermission.DELETE},
        }
    )


@pytest.mark.parametrize(
    ("role", "granted"),
    [
        (UserRole.ADMINISTRATOR, set(DefectPermission)),
        (UserRole.MANAGER, {DefectPermission.READ}),
        (UserRole.ENGINEER, {DefectPermission.READ}),
        (UserRole.PACKER, set[DefectPermission]()),
        (UserRole.OPERATOR, set[DefectPermission]()),
    ],
)
def test_roles_get_defect_catalog_permissions(role: UserRole, granted: set[DefectPermission]) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert {permission for permission in DefectPermission if permission in permissions} == granted


def test_verification_routes_require_verification_read() -> None:
    assert_routes_require(
        {
            "ListVerificationSessions": {VerificationPermission.READ},
            "GetVerificationSession": {VerificationPermission.READ},
            "ListPakChecks": {VerificationPermission.READ},
            "GetPakCheck": {VerificationPermission.READ},
        }
    )


@pytest.mark.parametrize(
    ("role", "granted"),
    [
        (UserRole.ADMINISTRATOR, True),
        (UserRole.MANAGER, True),
        (UserRole.ENGINEER, True),
        (UserRole.PACKER, False),
        (UserRole.OPERATOR, False),
    ],
)
def test_roles_get_verification_read(role: UserRole, granted: bool) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert (VerificationPermission.READ in permissions) is granted
