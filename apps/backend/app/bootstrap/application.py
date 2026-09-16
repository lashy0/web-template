"""Wire existing adapters and compatibility services at process boundaries."""

from dataclasses import dataclass

from fastapi import FastAPI
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.domains.equipment.pak.authentication import PakMachineAuthenticator
from app.domains.identity.users.commands import BootstrapFirstAdministrator
from app.infrastructure.database.session import Database, create_database
from app.infrastructure.domain_adapters.verification import (
    ProductionVerificationKgAdapter,
    SqlAlchemyLatestVerificationProjection,
    SqlAlchemyVerificationHistoryProvider,
    adapt_pak,
)
from app.infrastructure.hydra.client import (
    HydraOAuthClientManager,
    HydraTokenIntrospector,
)
from app.infrastructure.hydra.pak import HydraPakTokenIntrospectorAdapter
from app.infrastructure.kratos.client import KratosIdentityManager, KratosSessionVerifier
from app.infrastructure.kratos.users import KratosUserIdentityProvider
from app.infrastructure.post_commit import InProcessPostCommitExecutor, preparation_effect_executor
from app.infrastructure.redis.client import create_redis_client
from app.infrastructure.redis.preparation_notifier import RedisProgressNotifier
from app.worker.preparation_dispatcher import CeleryWorkDispatcher


@dataclass(slots=True)
class ApplicationComponents:
    """Concrete dependencies kept together until their contexts are extracted."""

    database: Database
    redis: Redis
    session_verifier: KratosSessionVerifier
    identity_manager: KratosIdentityManager
    hydra_client_manager: HydraOAuthClientManager
    pak_machine_authenticator: PakMachineAuthenticator
    post_commit_executor: InProcessPostCommitExecutor

    def install(self, app: FastAPI) -> None:
        """Expose compatibility dependencies expected by the legacy routers."""
        app.state.database = self.database
        app.state.redis = self.redis
        app.state.session_verifier = self.session_verifier
        app.state.identity_manager = self.identity_manager
        app.state.hydra_client_manager = self.hydra_client_manager
        app.state.pak_machine_authenticator = self.pak_machine_authenticator
        app.state.verification_kg_port_factory = ProductionVerificationKgAdapter
        app.state.verification_pak_adapter = adapt_pak
        app.state.production_verification_history_factory = SqlAlchemyVerificationHistoryProvider
        app.state.pak_verification_history_factory = SqlAlchemyVerificationHistoryProvider
        app.state.latest_verification_projection_port_factory = (
            SqlAlchemyLatestVerificationProjection
        )
        app.state.post_commit_executor = self.post_commit_executor

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
    pak_tokens = HydraPakTokenIntrospectorAdapter(HydraTokenIntrospector(settings))
    notifier = RedisProgressNotifier()
    progress_effect_executor = preparation_effect_executor(notifier)
    dispatcher = CeleryWorkDispatcher(database.session_factory, notifier, progress_effect_executor)

    return ApplicationComponents(
        database=database,
        redis=create_redis_client(settings),
        session_verifier=KratosSessionVerifier(settings),
        identity_manager=identity_manager,
        hydra_client_manager=hydra_client_manager,
        pak_machine_authenticator=PakMachineAuthenticator(database.session_factory, pak_tokens),
        post_commit_executor=preparation_effect_executor(notifier, dispatcher=dispatcher),
    )


async def bootstrap_first_administrator() -> None:
    """Run the existing administrator bootstrap through the composition root."""
    settings = get_settings()
    setup_logging(settings)
    database = create_database(settings)

    try:
        user = await BootstrapFirstAdministrator(
            database.session_factory,
            KratosUserIdentityProvider(KratosIdentityManager(settings)),
        ).execute(
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
