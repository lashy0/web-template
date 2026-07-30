from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from loguru import logger

from app.api.main import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.core.version import APP_VERSION
from app.database.session import create_database
from app.middleware.request_context import RequestContextMiddleware
from app.redis.client import create_redis_client


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings

    setup_logging(settings)

    database = create_database(settings)
    app.state.database = database

    redis = create_redis_client(settings)
    app.state.redis = redis

    logger.bind(event="application_startup").info("Application startup")

    try:
        yield
    finally:
        logger.bind(event="application_shutdown").info("Application shutdown")

        await redis.aclose()
        await database.close()
        await logger.complete()


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.PROJECT_NAME,
        version=APP_VERSION,
        openapi_url=(f"{app_settings.API_PREFIX}/openapi.json"),
        generate_unique_id_function=custom_generate_unique_id,
        lifespan=lifespan,
        debug=app_settings.DEBUG,
    )

    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    app.add_middleware(
        RequestContextMiddleware,
        quiet_path_prefixes=(f"{app_settings.API_PREFIX.rstrip('/')}/health",),
    )

    app.include_router(api_router, prefix=app_settings.API_PREFIX)

    return app
