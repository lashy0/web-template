import pytest

from app.auth.permissions import Permission as LegacyPermission
from app.bootstrap.permissions import ALL_PERMISSIONS
from app.core.config import Settings
from app.main import create_app
from app.shared.security import Permission, permission_registry


@pytest.mark.unit
def test_create_app_explicitly_installs_composed_permission_registry() -> None:
    create_app(Settings())

    registry = permission_registry()
    assert registry.all_permissions == ALL_PERMISSIONS
    assert LegacyPermission is Permission
    assert all(isinstance(permission, str) for permission in registry.all_permissions)
