"""Wire existing adapters and compatibility services at process boundaries."""

from dataclasses import dataclass

from fastapi import FastAPI
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.infrastructure.database.session import Database, create_database
from app.infrastructure.hydra.client import (
    HydraOAuthClientManager,
    HydraTokenIntrospector,
)
from app.infrastructure.kratos.client import KratosIdentityManager, KratosSessionVerifier
from app.infrastructure.redis.client import create_redis_client
from app.modules.batch.services import BatchManagementService
from app.modules.defects.services import DefectManagementService
from app.modules.kg.services import (
    KgDevEuiPrefixManagementService,
    KgManagementService,
    KgVersionManagementService,
)
from app.modules.pak.services import PakManagementService, PakTestCatalogService
from app.modules.production_order.services import ProductionOrderManagementService
from app.modules.users.services import UserManagementService
from app.modules.verification.services import VerificationManagementService


@dataclass(slots=True)
class ApplicationComponents:
    """Concrete dependencies kept together until their contexts are extracted."""

    database: Database
    redis: Redis
    session_verifier: KratosSessionVerifier
    identity_manager: KratosIdentityManager
    hydra_client_manager: HydraOAuthClientManager
    user_management: UserManagementService
    pak_management: PakManagementService
    pak_test_catalog: PakTestCatalogService
    kg_management: KgManagementService
    kg_dev_eui_prefix_management: KgDevEuiPrefixManagementService
    kg_version_management: KgVersionManagementService
    production_order_management: ProductionOrderManagementService
    batch_management: BatchManagementService
    verification_management: VerificationManagementService
    defect_management: DefectManagementService

    def install(self, app: FastAPI) -> None:
        """Expose compatibility dependencies expected by the legacy routers."""
        app.state.database = self.database
        app.state.redis = self.redis
        app.state.session_verifier = self.session_verifier
        app.state.identity_manager = self.identity_manager
        app.state.hydra_client_manager = self.hydra_client_manager
        app.state.user_management = self.user_management
        app.state.pak_management = self.pak_management
        app.state.pak_test_catalog = self.pak_test_catalog
        app.state.kg_management = self.kg_management
        app.state.kg_dev_eui_prefix_management = self.kg_dev_eui_prefix_management
        app.state.kg_version_management = self.kg_version_management
        app.state.production_order_management = self.production_order_management
        app.state.batch_management = self.batch_management
        app.state.verification_management = self.verification_management
        app.state.defect_management = self.defect_management

    @staticmethod
    def audit_writer(session: AsyncSession) -> TransactionalAuditWriter:
        """Create a session-bound audit collaborator for a future command."""
        # The concrete type is intentionally local to callers that own a DB session.
        return TransactionalAuditWriter.from_session(session)

    async def close(self) -> None:
        await self.redis.aclose()
        await self.database.close()


def create_application_components(settings: Settings) -> ApplicationComponents:
    """Create concrete adapters and legacy service facades in one place."""
    database = create_database(settings)
    identity_manager = KratosIdentityManager(settings)
    hydra_client_manager = HydraOAuthClientManager(settings)

    return ApplicationComponents(
        database=database,
        redis=create_redis_client(settings),
        session_verifier=KratosSessionVerifier(settings),
        identity_manager=identity_manager,
        hydra_client_manager=hydra_client_manager,
        user_management=UserManagementService(database.session_factory, identity_manager),
        pak_management=PakManagementService(
            database.session_factory,
            hydra_client_manager,
            HydraTokenIntrospector(settings),
            settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
        ),
        pak_test_catalog=PakTestCatalogService(database.session_factory),
        kg_management=KgManagementService(database.session_factory),
        kg_dev_eui_prefix_management=KgDevEuiPrefixManagementService(database.session_factory),
        kg_version_management=KgVersionManagementService(database.session_factory),
        production_order_management=ProductionOrderManagementService(database.session_factory),
        batch_management=BatchManagementService(database.session_factory),
        verification_management=VerificationManagementService(
            database.session_factory,
            reopen_inactivity_minutes=settings.VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES,
            session_ttl_minutes=settings.VERIFICATION_SESSION_TTL_MINUTES,
        ),
        defect_management=DefectManagementService(database.session_factory),
    )


async def bootstrap_first_administrator() -> None:
    """Run the existing administrator bootstrap through the composition root."""
    settings = get_settings()
    setup_logging(settings)
    database = create_database(settings)

    try:
        service = UserManagementService(database.session_factory, KratosIdentityManager(settings))
        user = await service.bootstrap_first_administrator(
            name=settings.BOOTSTRAP_ADMIN_NAME,
            login=settings.BOOTSTRAP_ADMIN_LOGIN,
            password_loader=settings.bootstrap_admin_password,
        )
        if user is None:
            logger.info("First-administrator bootstrap skipped because users already exist")
        else:
            logger.info("First-administrator bootstrap completed")
    finally:
        await database.close()
        await logger.complete()
