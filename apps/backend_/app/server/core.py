from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import RepositoryError
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPlugin

from app.__metadata__ import __version__
from app.config import (
    AppSettings,
    HydraSettings,
    KratosSettings,
    Settings,
    VerificationSettings,
    get_settings,
)
from app.db import models as m
from app.lib.exceptions import (
    ApplicationError,
    exception_group_to_http_response,
    exception_to_http_response,
)
from app.lib.hydra import HydraClient, provide_hydra_client
from app.lib.kratos import KratosClient, provide_kratos_client
from app.lib.uow import UnitOfWork, provide_uow
from app.server import plugins
from app.server.authentication import SessionVerifier, create_authentication_middleware
from app.server.authorization import create_authorization_policy

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class ApplicationCore(InitPlugin):
    """Compose the application from one set of settings.

    Everything environment-specific (database, CORS, Kratos, Hydra) is built from
    ``settings``, so an application built with other settings, e.g. in tests,
    shares no connections with the default one. ``session_verifier`` replaces
    the Kratos Public API check of browser sessions.
    """

    __slots__ = ("_session_verifier", "_settings", "app_slug")

    app_slug: str

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_verifier: SessionVerifier | None = None,
    ) -> None:
        self._settings = settings
        self._session_verifier = session_verifier

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        settings = self._settings or get_settings()
        alchemy = settings.db.get_config()

        self.app_slug = settings.app.slug

        app_config.debug = settings.app.debug

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.name,
            version=__version__,
            render_plugins=[
                ScalarRenderPlugin(version="latest"),
            ],
        )

        app_config.cors_config = settings.app.get_cors_config()
        app_config.exception_handlers.update(  # pyright: ignore[reportUnknownMemberType]
            {
                ApplicationError: exception_to_http_response,
                RepositoryError: exception_to_http_response,
                ExceptionGroup: exception_group_to_http_response,
            }
        )
        app_config.state["authorization_policy"] = create_authorization_policy()

        app_config.plugins.extend(
            [
                SQLAlchemyPlugin(config=alchemy),
                plugins.autowire,
                plugins.create_task_queue(settings),
            ]
        )
        app_config.middleware.append(
            create_authentication_middleware(
                settings.kratos,
                session_factory=alchemy.get_session,
                verifier=self._session_verifier,
            )
        )

        app_config.signature_namespace.update(
            {
                "AppSettings": AppSettings,
                "HydraSettings": HydraSettings,
                "KratosSettings": KratosSettings,
                "HydraClient": HydraClient,
                "KratosClient": KratosClient,
                "UnitOfWork": UnitOfWork,
                "VerificationSettings": VerificationSettings,
                "m": m,
            }
        )

        def provide_app_settings() -> AppSettings:
            return settings.app

        def provide_kratos_settings() -> KratosSettings:
            return settings.kratos

        def provide_hydra_settings() -> HydraSettings:
            return settings.hydra

        def provide_verification_settings() -> VerificationSettings:
            return settings.verification

        app_config.dependencies.update(
            {
                "settings": Provide(
                    provide_app_settings,
                    sync_to_thread=False,
                ),
                "kratos_settings": Provide(
                    provide_kratos_settings,
                    sync_to_thread=False,
                ),
                "hydra_settings": Provide(
                    provide_hydra_settings,
                    sync_to_thread=False,
                ),
                "verification_settings": Provide(
                    provide_verification_settings,
                    sync_to_thread=False,
                ),
                "hydra": Provide(
                    provide_hydra_client,
                    sync_to_thread=False,
                ),
                "kratos": Provide(
                    provide_kratos_client,
                    sync_to_thread=False,
                ),
                "uow": Provide(provide_uow),
            }
        )

        return app_config
