import pytest

from app.core.config import Settings
from app.worker.celery_app import create_celery_app
from app.worker.tasks import ping


@pytest.mark.unit
def test_celery_app_uses_configured_redis_and_delivery_settings() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_REDIS_HOST": "redis.internal",
            "BACKEND_REDIS_PORT": 6380,
            "BACKEND_REDIS_PASSWORD": "secret",
            "BACKEND_REDIS_PREFIX": "test-app",
        }
    )

    celery = create_celery_app(settings)

    assert celery.conf.broker_url == str(settings.redis_url)
    assert celery.conf.task_acks_late is True
    assert celery.conf.worker_prefetch_multiplier == 1
    assert celery.conf.worker_enable_remote_control is False
    assert celery.conf.broker_transport_options == {"global_keyprefix": "test-app:celery:"}


@pytest.mark.unit
def test_ping_task_returns_pong() -> None:
    assert ping.run() == "pong"
