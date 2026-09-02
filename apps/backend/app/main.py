import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from loguru import logger

from app.api.errors import install_error_handlers
from app.api.main import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.core.version import APP_VERSION
from app.infrastructure.database.session import create_database
from app.infrastructure.hydra.client import (
    HydraMachineTokenIssuer,
    HydraOAuthClientManager,
    HydraTokenIntrospector,
)
from app.infrastructure.kratos.client import KratosIdentityManager, KratosSessionVerifier
from app.infrastructure.redis.client import create_redis_client
from app.middleware.csrf import JsonOriginMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.modules.pak.service import PakManagementService, PakTestCatalogService
from app.modules.users.service import UserManagementService
from app.modules.kg.service import KgManagementService, KgDevEuiPrefixManagementService
from app.modules.batch.service import BatchManagementService
from app.modules.verification.service import VerificationManagementService
from app.modules.defects.service import DefectManagementService


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings

    setup_logging(settings)

    database = create_database(settings)
    app.state.database = database

    app.state.session_verifier = KratosSessionVerifier(settings)
    app.state.identity_manager = KratosIdentityManager(settings)

    app.state.user_management = UserManagementService(
        database.session_factory, app.state.identity_manager
    )

    app.state.hydra_client_manager = HydraOAuthClientManager(settings)

    app.state.pak_management = PakManagementService(
        database.session_factory,
        app.state.hydra_client_manager,
        HydraTokenIntrospector(settings),
        HydraMachineTokenIssuer(settings),
        settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
    )
    app.state.pak_test_catalog = PakTestCatalogService(
        database.session_factory,
    )

    app.state.kg_management = KgManagementService(
        database.session_factory,
    )

    app.state.kg_dev_eui_prefix_management = KgDevEuiPrefixManagementService(
        database.session_factory,
    )

    app.state.batch_management = BatchManagementService(
        database.session_factory,
    )

    app.state.verification_management = VerificationManagementService(
        database.session_factory,
        reopen_inactivity_minutes=(
            settings.VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES
        ),
        session_ttl_minutes=(
            settings.VERIFICATION_SESSION_TTL_MINUTES
        ),
    )

    app.state.defect_management = DefectManagementService(
        database.session_factory,
    )

    redis = create_redis_client(settings)
    app.state.redis = redis

    logger.bind(event="application_startup").info("Application startup")

    reconcile_task = None
    verification_sweeper_task = None

    async def reconcile_forever() -> None:
        while True:
            try:
                await app.state.user_management.reconcile()

            except Exception:
                logger.bind(event="kratos.reconcile_failed").exception(
                    "Kratos reconciliation failed"
                )

            await asyncio.sleep(settings.KRATOS_RECONCILE_INTERVAL)

    async def verification_sweeper_forever() -> None:
        while True:
            try:
                expired = await app.state.verification_management.expire_stale_sessions()

                if expired:
                    logger.bind(
                        event="verification.sessions_expired",
                        count=expired,
                    ).info(
                        "Expired stale verification sessions"
                    )

            except Exception:
                logger.bind(event="verification.sweeper_failed").exception(
                    "Verification session sweep failed"
                )

            await asyncio.sleep(settings.VERIFICATION_SWEEP_INTERVAL_SECONDS)

    reconcile_task = asyncio.create_task(reconcile_forever())
    verification_sweeper_task = asyncio.create_task(verification_sweeper_forever())

    try:
        yield

    finally:
        logger.bind(event="application_shutdown").info("Application shutdown")

        if reconcile_task is not None:
            reconcile_task.cancel()

            try:
                await reconcile_task

            except asyncio.CancelledError:
                pass

        if verification_sweeper_task is not None:
            verification_sweeper_task.cancel()

            try:
                await verification_sweeper_task

            except asyncio.CancelledError:
                pass

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
        openapi_url=(f"{app_settings.API_PREFIX}/openapi.json" if app_settings.DEBUG else None),
        docs_url=(f"{app_settings.API_PREFIX}/docs" if app_settings.DEBUG else None),
        redoc_url=None,
        openapi_tags=[
            {
                "name": "health",
                "description": "Application liveness and dependency readiness checks.",
            },
        ],
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
        JsonOriginMiddleware,
        allowed_origins=tuple(app_settings.all_cors_origins),
    )

    app.add_middleware(
        RequestContextMiddleware,
        quiet_path_prefixes=(f"{app_settings.API_PREFIX.rstrip('/')}/health",),
    )

    app.include_router(api_router, prefix=app_settings.API_PREFIX)
    install_error_handlers(app)

    return app
