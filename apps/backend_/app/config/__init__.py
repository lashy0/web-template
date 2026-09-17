from app.config.database import DatabaseSettings
from app.config.kratos import KratosSettings
from app.config.settings import (
    AppSettings,
    Settings,
    get_settings,
    provide_app_settings,
    provide_kratos_settings,
)

_settings = get_settings()

alchemy = _settings.db.get_config()
cors = _settings.app.get_cors_config()


__all__ = [
    "AppSettings",
    "DatabaseSettings",
    "KratosSettings",
    "Settings",
    "alchemy",
    "cors",
    "get_settings",
    "provide_app_settings",
    "provide_kratos_settings",
]
