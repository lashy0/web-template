"""Worker adapter compatibility boundary."""

from app.worker.celery_app import celery_app, create_celery_app

__all__ = ["celery_app", "create_celery_app"]
