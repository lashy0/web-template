from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPluginProtocol

from app import config
from app.__metadata__ import __version__
from app.config import (
    AppSettings,
    KratosSettings,
    get_settings,
    provide_app_settings,
    provide_kratos_settings,
)
from app.lib.kratos import KratosClient, provide_kratos_client
from app.server import plugins

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class ApplicationCore(InitPluginProtocol):
    __slots__ = ("app_slug",)

    app_slug: str

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        settings = get_settings()

        self.app_slug = settings.app.slug

        self.kratos_client = provide_kratos_client(settings.kratos)

        app_config.debug = settings.app.debug

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.name,
            version=__version__,
            render_plugins=[
                ScalarRenderPlugin(version="latest"),
            ],
        )

        app_config.cors_config = config.cors

        app_config.plugins.extend(
            [
                plugins.alchemy,
                plugins.domain,
            ]
        )

        app_config.signature_namespace.update(
            {
                "AppSettings": AppSettings,
                "KratosSettings": KratosSettings,
                "KratosClient": KratosClient,
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
                "kratos": Provide(
                    provide_kratos_client,
                    sync_to_thread=False,
                ),
            }
        )

        return app_config
