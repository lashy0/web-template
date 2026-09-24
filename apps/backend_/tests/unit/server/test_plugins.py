import pytest
from litestar_autowire import clear_autowire_cache

from app.server.asgi import create_app

pytestmark = pytest.mark.unit


def test_autowire_registers_every_domain_controller() -> None:
    """Autowire imports ``controllers`` of each package in ``app.domain``.

    A domain whose controller module fails to import stops the application, but a
    controller placed outside a ``controllers`` module is silently not registered.
    Update this set when a controller is added or removed.
    """
    clear_autowire_cache()

    handlers = [handler for route in create_app().routes for handler in getattr(route, "route_handlers", ())]
    controllers = {
        handler.fn.__qualname__.partition(".")[0]
        for handler in handlers
        if handler.fn.__module__.startswith("app.domain.")
    }

    assert controllers == {
        "KgPrefixController",
        "KgVersionController",
        "PakDeviceController",
        "ProductionOrderController",
        "ProfileController",
        "SystemController",
        "UserController",
    }
