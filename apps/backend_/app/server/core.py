from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import RepositoryError
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPluginProtocol

from app import config
from app.__metadata__ import __version__
from app.config import (
    AppSettings,
    HydraSettings,
    KratosSettings,
    get_settings,
    provide_app_settings,
    provide_hydra_settings,
    provide_kratos_settings,
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
from app.server.authentication import create_authentication_middleware
from app.server.authorization import create_authorization_policy

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class ApplicationCore(InitPluginProtocol):
    __slots__ = ("app_slug",)

    app_slug: str

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        settings = get_settings()

        self.app_slug = settings.app.slug

        app_config.debug = settings.app.debug

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.name,
            version=__version__,
            render_plugins=[
                ScalarRenderPlugin(version="latest"),
            ],
        )

        app_config.cors_config = config.cors
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
                plugins.alchemy,
                plugins.domain,
            ]
        )
        app_config.middleware.append(create_authentication_middleware(settings.kratos))

        app_config.signature_namespace.update(
            {
                "AppSettings": AppSettings,
                "HydraSettings": HydraSettings,
                "KratosSettings": KratosSettings,
                "HydraClient": HydraClient,
                "KratosClient": KratosClient,
                "UnitOfWork": UnitOfWork,
                "m": m,
            }
        )

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
