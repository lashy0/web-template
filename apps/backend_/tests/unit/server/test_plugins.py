import pytest
from litestar_autowire import clear_autowire_cache
from litestar_saq import SAQPlugin

from app.config import get_settings
from app.domain.quality.tasks import expire_stale_verification_sessions
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
        "BatchController",
        "BatchReceiptController",
        "DefectGroupController",
        "DefectTypeController",
        "KgPrefixController",
        "KgUnitController",
        "KgVersionController",
        "MachineVerificationController",
        "PakCheckController",
        "PakDeviceController",
        "ProductionOrderController",
        "ProfileController",
        "SystemController",
        "UserController",
        "VerificationSessionController",
    }


def test_task_queue_is_named_after_the_redis_prefix() -> None:
    """The runtime Redis ACL allows SAQ keys only under ``saq:<prefix>:*``."""
    plugin = create_app().plugins.get(SAQPlugin)

    assert list(plugin.get_queues().queues) == [get_settings().redis.prefix]


def test_workers_do_not_start_with_the_server_by_default() -> None:
    assert create_app().plugins.get(SAQPlugin).config.use_server_lifespan is False


def test_stale_verification_sessions_are_swept_every_minute() -> None:
    (queue_config,) = create_app().plugins.get(SAQPlugin).config.queue_configs

    assert [(job.function, job.cron) for job in queue_config.scheduled_tasks] == [
        (expire_stale_verification_sessions, "* * * * *"),
    ]
