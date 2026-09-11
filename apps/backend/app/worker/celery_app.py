from celery import Celery  # type: ignore[import-untyped]

from app.core.config import Settings, get_settings


def create_celery_app(settings: Settings | None = None) -> Celery:
    """Create the Celery application backed by the configured Redis instance."""
    app_settings = settings or get_settings()
    celery = Celery(
        "web_app",
        broker=str(app_settings.redis_url),
        include=["app.worker.tasks"],
    )

    celery.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        worker_enable_remote_control=False,
        broker_transport_options={
            "global_keyprefix": f"{app_settings.REDIS_PREFIX.strip(':')}:celery:",
        },
    )

    return celery


celery_app = create_celery_app()
