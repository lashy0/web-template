"""Wire existing adapters and compatibility services at process boundaries."""

from dataclasses import dataclass

from fastapi import FastAPI
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.contexts.equipment.pak.adapters import adapt_pak
from app.contexts.equipment.pak.authentication import PakMachineAuthenticator
from app.contexts.equipment.pak.commands import (
    CreatePak,
    DeletePak,
    GetPakAccessKey,
    RotatePakAccessKey,
    SetPakActive,
    SetPakArchived,
    UpdatePak,
)
from app.contexts.equipment.pak.queries import PakQueries
from app.contexts.production.batches.commands import DeleteBatch
from app.contexts.production.compat.verification import QualityVerificationHistoryAdapter
from app.contexts.production.compat.verification_kg import ProductionVerificationKgAdapter
from app.contexts.production.production_orders.service import ProductionOrderManagementService
from app.contexts.quality.tests.catalog import PakTestCatalog
from app.contexts.quality.verification.adapters import QualityPakVerificationHistoryAdapter
from app.contexts.quality.verification.commands.reconcile import reconcile_stale_sessions
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.infrastructure.database.session import Database, create_database
from app.infrastructure.hydra.client import (
    HydraOAuthClientManager,
    HydraTokenIntrospector,
)
from app.infrastructure.hydra.pak import (
    HydraPakOAuthClientAdapter,
    HydraPakTokenIntrospectorAdapter,
)
from app.infrastructure.kratos.client import KratosIdentityManager, KratosSessionVerifier
from app.infrastructure.redis.client import create_redis_client
from app.infrastructure.redis.preparation_notifier import RedisProgressNotifier
from app.modules.batch.services import BatchManagementService
from app.modules.defects.services import DefectManagementService
from app.modules.users.services import UserManagementService


@dataclass(slots=True)
class ApplicationComponents:
    """Concrete dependencies kept together until their contexts are extracted."""

    database: Database
    redis: Redis
    session_verifier: KratosSessionVerifier
    identity_manager: KratosIdentityManager
    hydra_client_manager: HydraOAuthClientManager
    user_management: UserManagementService
    pak_queries: PakQueries
    create_pak: CreatePak
    update_pak: UpdatePak
    set_pak_active: SetPakActive
    set_pak_archived: SetPakArchived
    delete_pak: DeletePak
    get_pak_access_key: GetPakAccessKey
    rotate_pak_access_key: RotatePakAccessKey
    pak_machine_authenticator: PakMachineAuthenticator
    pak_test_catalog: PakTestCatalog
    production_order_management: ProductionOrderManagementService
    batch_management: BatchManagementService
    delete_batch: DeleteBatch
    defect_management: DefectManagementService

    def install(self, app: FastAPI) -> None:
        """Expose compatibility dependencies expected by the legacy routers."""
        app.state.database = self.database
        app.state.redis = self.redis
        app.state.session_verifier = self.session_verifier
        app.state.identity_manager = self.identity_manager
        app.state.hydra_client_manager = self.hydra_client_manager
        app.state.user_management = self.user_management
        app.state.pak_queries = self.pak_queries
        app.state.create_pak = self.create_pak
        app.state.update_pak = self.update_pak
        app.state.set_pak_active = self.set_pak_active
        app.state.set_pak_archived = self.set_pak_archived
        app.state.delete_pak = self.delete_pak
        app.state.get_pak_access_key = self.get_pak_access_key
        app.state.rotate_pak_access_key = self.rotate_pak_access_key
        app.state.pak_machine_authenticator = self.pak_machine_authenticator
        app.state.pak_test_catalog = self.pak_test_catalog
        app.state.production_order_management = self.production_order_management
        app.state.batch_management = self.batch_management
        app.state.delete_batch = self.delete_batch
        app.state.verification_kg_port_factory = ProductionVerificationKgAdapter
        app.state.verification_pak_adapter = adapt_pak
        app.state.reconcile_stale_verification_sessions = reconcile_stale_sessions
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
    pak_oauth = HydraPakOAuthClientAdapter(hydra_client_manager)
    pak_tokens = HydraPakTokenIntrospectorAdapter(HydraTokenIntrospector(settings))

    return ApplicationComponents(
        database=database,
        redis=create_redis_client(settings),
        session_verifier=KratosSessionVerifier(settings),
        identity_manager=identity_manager,
        hydra_client_manager=hydra_client_manager,
        user_management=UserManagementService(database.session_factory, identity_manager),
        pak_queries=PakQueries(database.session_factory),
        create_pak=CreatePak(
            database.session_factory, pak_oauth, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY
        ),
        update_pak=UpdatePak(database.session_factory),
        set_pak_active=SetPakActive(database.session_factory),
        set_pak_archived=SetPakArchived(database.session_factory),
        delete_pak=DeletePak(
            database.session_factory,
            pak_oauth,
            QualityPakVerificationHistoryAdapter,
            settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
        ),
        get_pak_access_key=GetPakAccessKey(
            database.session_factory, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY
        ),
        rotate_pak_access_key=RotatePakAccessKey(
            database.session_factory, pak_oauth, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY
        ),
        pak_machine_authenticator=PakMachineAuthenticator(database.session_factory, pak_tokens),
        pak_test_catalog=PakTestCatalog(database.session_factory),
        production_order_management=ProductionOrderManagementService(database.session_factory),
        batch_management=BatchManagementService(database.session_factory),
        delete_batch=DeleteBatch(
            database.session_factory,
            verification_history=QualityVerificationHistoryAdapter,
            notifier=RedisProgressNotifier(),
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
