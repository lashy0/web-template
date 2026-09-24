from functools import lru_cache
from pathlib import Path

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
)
from pydantic import AliasChoices, Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_POSTGRES_MIGRATOR_USER = "otk_app_migrator"
_POSTGRES_RUNTIME_USER = "otk_app_runtime"

_APP_DIR = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _APP_DIR / "db" / "migrations"

# Shared by the Litestar CLI config and ``migrations/env.py`` so both track the same revision table.
MIGRATION_VERSION_TABLE = "ddl_version"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    database_url_override: PostgresDsn | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
    )

    postgres_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("BACKEND_POSTGRES_HOST", "POSTGRES_HOST"),
    )

    postgres_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("BACKEND_POSTGRES_PORT", "POSTGRES_PORT"),
    )

    postgres_db: str = Field(
        default="otk_app",
        validation_alias=AliasChoices("BACKEND_POSTGRES_DB", "POSTGRES_DB"),
    )

    postgres_runtime_password: SecretStr | None = Field(
        default=None,
        validation_alias="BACKEND_POSTGRES_RUNTIME_PASSWORD",
    )

    postgres_migrator_password: SecretStr | None = Field(
        default=None,
        validation_alias="BACKEND_POSTGRES_MIGRATOR_PASSWORD",
    )

    @property
    def database_url(self) -> PostgresDsn:
        if self.database_url_override is not None:
            return self.database_url_override

        if self.postgres_runtime_password is None:
            raise ValueError("BACKEND_POSTGRES_RUNTIME_PASSWORD is required when DATABASE_URL is not set")

        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=_POSTGRES_RUNTIME_USER,
            password=self.postgres_runtime_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    @property
    def migration_database_url(self) -> PostgresDsn:
        if self.database_url_override is not None:
            return self.database_url_override

        if self.postgres_migrator_password is None:
            raise ValueError("BACKEND_POSTGRES_MIGRATOR_PASSWORD is required when DATABASE_URL is not set")

        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=_POSTGRES_MIGRATOR_USER,
            password=self.postgres_migrator_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    def get_config(self) -> SQLAlchemyAsyncConfig:
        return SQLAlchemyAsyncConfig(
            connection_string=str(self.database_url),
            session_config=AsyncSessionConfig(
                expire_on_commit=False,
            ),
            alembic_config=AlembicAsyncConfig(
                version_table_name=MIGRATION_VERSION_TABLE,
                script_config="alembic.ini",
                script_location=str(_MIGRATIONS_DIR),
            ),
        )


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()
