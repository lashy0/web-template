import pytest

from app.domain.pak.permissions import PakPermission
from tests.unit.route_permissions import assert_routes_require

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_pak_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListPakDevices": {PakPermission.READ},
            "GetPakDevice": {PakPermission.READ},
            "CreatePakDevice": {PakPermission.CREATE},
            "UpdatePakDevice": {PakPermission.UPDATE},
            "ActivatePakDevice": {PakPermission.SET_ACTIVE},
            "DeactivatePakDevice": {PakPermission.SET_ACTIVE},
            "ArchivePakDevice": {PakPermission.ARCHIVE},
            "RestorePakDevice": {PakPermission.ARCHIVE},
            "DeletePakDevice": {PakPermission.DELETE},
            "GetPakAccessKey": {PakPermission.READ_ACCESS_KEY},
            "RotatePakAccessKey": {PakPermission.ROTATE_ACCESS_KEY},
        }
    )
