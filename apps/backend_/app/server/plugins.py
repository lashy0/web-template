from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog
from litestar.logging.config import LoggingConfig, StructLoggingConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_saq import CronJob, QueueConfig, SAQConfig, SAQPlugin

from app.lib.log import log_unhandled_exception, stdlib_processors, structlog_processors

if TYPE_CHECKING:
    from app.config import LogSettings, Settings

autowire = AutowirePlugin(AutowireConfig(domain_packages=["app.domain"]))

TASKS: list[str] = []
"""Dotted paths of the functions a worker runs on request."""

SCHEDULED_TASKS = [
    CronJob(
        function="app.domain.quality.tasks.expire_stale_verification_sessions",
        cron="* * * * *",
        timeout=50,
    ),
]
"""Recurring tasks; SAQ runs each once per schedule however many workers there are."""


def create_task_queue(settings: Settings) -> SAQPlugin:
    """Build the SAQ plugin with one queue named after the Redis prefix.

    The queue name keeps SAQ's keys inside the runtime ACL user's
    ``saq:<prefix>:*`` namespace.
    """
    return SAQPlugin(
        config=SAQConfig(
            use_server_lifespan=settings.queue.workers_in_server,
            queue_configs=[
                QueueConfig(
                    name=settings.redis.prefix,
                    dsn=str(settings.redis.url),
                    tasks=TASKS,
                    scheduled_tasks=SCHEDULED_TASKS,
                    startup=["app.lib.worker.on_startup"],
                    shutdown=["app.lib.worker.on_shutdown"],
                ),
            ],
        ),
    )


def create_logging(settings: LogSettings) -> StructlogPlugin:
    """Build structured logging to stdout for the application and the libraries it uses.

    Logs are readable text in a terminal and JSON otherwise, or always with
    ``BACKEND_LOG_JSON``. Records from standard ``logging`` go through
    Litestar's queue listener and the same renderer.
    """
    as_json = settings.json_output or not sys.stdout.isatty()
    level = logging.getLevelNamesMapping()[settings.level]

    def library(library_level: str | int) -> dict[str, Any]:
        return {"level": library_level, "handlers": ["queue_listener"], "propagate": False}

    return StructlogPlugin(
        config=StructlogConfig(
            # app.lib.log.log_request writes one line per request instead.
            enable_middleware_logging=False,
            structlog_logging_config=StructLoggingConfig(
                processors=structlog_processors(as_json=as_json),
                logger_factory=structlog.WriteLoggerFactory(),
                wrapper_class=structlog.make_filtering_bound_logger(level),
                # Settings of an application built later (tests) must reach loggers already used.
                cache_logger_on_first_use=False,
                log_exceptions="always",
                exception_logging_handler=log_unhandled_exception,
                standard_lib_logging_config=LoggingConfig(
                    root={"level": settings.level, "handlers": ["queue_listener"]},
                    formatters={
                        "standard": {
                            "()": structlog.stdlib.ProcessorFormatter,
                            "processors": stdlib_processors(as_json=as_json),
                        },
                    },
                    handlers={
                        "console": {
                            "class": "logging.StreamHandler",
                            "stream": "ext://sys.stdout",
                            "formatter": "standard",
                        },
                    },
                    loggers={
                        "litestar": library(settings.level),
                        "sqlalchemy.engine": library(settings.sqlalchemy_level),
                        "sqlalchemy.pool": library(settings.sqlalchemy_level),
                        "saq": library(settings.saq_level),
                        "uvicorn.error": library(settings.level),
                        # Replaced by the request line of app.lib.log.log_request.
                        "uvicorn.access": library(logging.WARNING),
                        "httpx": library(max(level, logging.WARNING)),
                        "httpcore": library(max(level, logging.WARNING)),
                    },
                ),
            ),
        )
    )
