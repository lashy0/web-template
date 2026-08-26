import logging
import sys
from types import FrameType
from typing import cast

from loguru import logger

from app.core.config import Settings

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS!UTC} UTC</green> | "
    "<level>{level: <8}</level> | "
    "pid={process.id} | "
    "request_id={extra[request_id]} | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = cast("FrameType", frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(settings: Settings) -> None:
    logger.remove()

    logger.configure(
        extra={
            "request_id": None,
            "correlation_id": None,
            "trace_id": None,
            "span_id": None,
            "service": settings.PROJECT_NAME,
        }
    )

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=LOG_FORMAT,
        serialize=settings.LOG_JSON,
        colorize=False if settings.LOG_JSON else None,
        enqueue=True,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
    )

    intercept_handler = InterceptHandler()

    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
    ):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [intercept_handler]
        logging_logger.propagate = False
