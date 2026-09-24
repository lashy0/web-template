import pytest

from app.utils.domain import clear_discovery_cache, discover_domain_controllers

pytestmark = pytest.mark.unit


def test_discovers_every_domain_controller() -> None:
    """Discovery skips modules that fail to import, so a broken import would drop routes silently.

    Update this set when a controller is added or removed.
    """
    clear_discovery_cache()

    controllers = {controller.__name__ for controller in discover_domain_controllers(["app.domain"])}

    assert controllers == {
        "PakDeviceController",
        "ProductionOrderController",
        "ProfileController",
        "SystemController",
        "UserController",
    }
