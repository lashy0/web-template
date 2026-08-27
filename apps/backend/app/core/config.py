import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_CORS_ORIGINS_FORMAT_ERROR = (
    "BACKEND_CORS_ORIGINS must be a JSON array of HTTP or HTTPS origins, "
    "for example '[\"http://localhost:5173\"]'"
)
_POSTGRES_MIGRATOR_USER = "web_app_migrator"
_POSTGRES_RUNTIME_USER = "web_app_runtime"
_REDIS_RUNTIME_USER = "web_app_runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    API_PREFIX: str = Field(
        default="",
        validation_alias="BACKEND_API_PREFIX",
    )
    PROJECT_NAME: str = Field(
        default="backend",
        validation_alias="BACKEND_PROJECT_NAME",
    )
    DEBUG: bool = Field(
        default=False,
        validation_alias="BACKEND_DEBUG",
    )

    # TODO: сделать проверку, которая проверяет, что LOG_LEVEL является допустимым
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias="BACKEND_LOG_LEVEL",
    )
    LOG_JSON: bool = Field(
        default=False,
        validation_alias="BACKEND_LOG_JSON",
    )

    CORS_ORIGINS: Annotated[list[AnyHttpUrl], NoDecode] = Field(
        default_factory=list,
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    # Health checks
    READINESS_TIMEOUT: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_READINESS_TIMEOUT",
    )

    # Ory Kratos
    KRATOS_PUBLIC_URL: str = Field(
        default="http://kratos:4433",
        validation_alias="BACKEND_KRATOS_PUBLIC_URL",
    )
    KRATOS_ADMIN_URL: str = Field(
        default="http://kratos:4434",
        validation_alias="BACKEND_KRATOS_ADMIN_URL",
    )
    KRATOS_SESSION_COOKIE: str = Field(
        default="ory_kratos_session", min_length=1, validation_alias="BACKEND_KRATOS_SESSION_COOKIE"
    )
    KRATOS_PUBLIC_TIMEOUT: float = Field(
        default=2.0, gt=0, validation_alias="BACKEND_KRATOS_PUBLIC_TIMEOUT"
    )
    KRATOS_ADMIN_TIMEOUT: float = Field(
        default=10.0, gt=0, validation_alias="BACKEND_KRATOS_ADMIN_TIMEOUT"
    )
    KRATOS_PUBLIC_CONCURRENCY: int = Field(
        default=20, ge=1, validation_alias="BACKEND_KRATOS_PUBLIC_CONCURRENCY"
    )
    KRATOS_ADMIN_CONCURRENCY: int = Field(
        default=4, ge=1, validation_alias="BACKEND_KRATOS_ADMIN_CONCURRENCY"
    )
    KRATOS_RECONCILE_INTERVAL: float = Field(
        default=300.0, gt=0, validation_alias="BACKEND_KRATOS_RECONCILE_INTERVAL"
    )
    KRATOS_RECONCILE_BATCH_SIZE: int = Field(
        default=500, ge=1, le=500, validation_alias="BACKEND_KRATOS_RECONCILE_BATCH_SIZE"
    )

    # Ory Hydra
    HYDRA_PUBLIC_URL: str = Field(
        default="http://hydra:4444",
        validation_alias="BACKEND_HYDRA_PUBLIC_URL",
    )
    HYDRA_ADMIN_URL: str = Field(
        default="http://hydra:4445",
        validation_alias="BACKEND_HYDRA_ADMIN_URL",
    )
    HYDRA_PUBLIC_TIMEOUT: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_HYDRA_PUBLIC_TIMEOUT",
    )
    HYDRA_ADMIN_TIMEOUT: float = Field(
        default=10.0,
        gt=0,
        validation_alias="BACKEND_HYDRA_ADMIN_TIMEOUT",
    )
    HYDRA_ADMIN_CONCURRENCY: int = Field(
        default=4,
        ge=1,
        validation_alias="BACKEND_HYDRA_ADMIN_CONCURRENCY",
    )

    # PAK access keys are encrypted with Fernet before they are stored locally.
    # This value deliberately has no default: deployments must supply a stable,
    # 32-byte URL-safe base64 Fernet key through their secret manager.
    PAK_ACCESS_KEY_ENCRYPTION_KEY: SecretStr | None = Field(
        default=None,
        validation_alias="BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY",
    )

    # First administrator bootstrap
    BOOTSTRAP_ADMIN_LOGIN: str = Field(
        default="admin",
        min_length=3,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9._-]{2,63}$",
        validation_alias="BACKEND_BOOTSTRAP_ADMIN_LOGIN",
    )
    BOOTSTRAP_ADMIN_NAME: str = Field(
        default="Администратор",
        min_length=1,
        max_length=128,
        validation_alias="BACKEND_BOOTSTRAP_ADMIN_NAME",
    )
    BOOTSTRAP_ADMIN_PASSWORD: SecretStr | None = Field(
        default=None,
        validation_alias="BACKEND_BOOTSTRAP_ADMIN_PASSWORD",
    )
    BOOTSTRAP_ADMIN_PASSWORD_FILE: Path | None = Field(
        default=None,
        validation_alias="BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE",
    )

    # Postgres
    DATABASE_URL: PostgresDsn | None = Field(
        default=None,
        validation_alias="BACKEND_DATABASE_URL",
    )
    MIGRATION_DATABASE_URL: PostgresDsn | None = Field(
        default=None,
        validation_alias="BACKEND_MIGRATION_DATABASE_URL",
    )
    POSTGRES_MIGRATOR_PASSWORD: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_MIGRATOR_PASSWORD",
            "POSTGRES_MIGRATOR_PASSWORD",
        ),
    )
    POSTGRES_PASSWORD: SecretStr = Field(
        default=SecretStr("changepassword"),
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_PASSWORD",
            "POSTGRES_RUNTIME_PASSWORD",
            "POSTGRES_PASSWORD",
        ),
    )
    POSTGRES_HOST: str = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_HOST",
            "POSTGRES_HOST",
        ),
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_PORT",
            "POSTGRES_PORT",
        ),
    )
    POSTGRES_DB: str = Field(
        default="web_app",
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_DB",
            "POSTGRES_DB",
        ),
    )

    # SQLAlchemy connection pool
    DB_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        validation_alias="BACKEND_DB_POOL_SIZE",
    )
    DB_MAX_OVERFLOW: int = Field(
        default=5,
        ge=0,
        validation_alias="BACKEND_DB_MAX_OVERFLOW",
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        ge=0,
        validation_alias="BACKEND_DB_POOL_TIMEOUT",
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        ge=0,
        validation_alias="BACKEND_DB_POOL_RECYCLE",
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True,
        validation_alias="BACKEND_DB_POOL_PRE_PING",
    )

    # Redis
    REDIS_URL: RedisDsn | None = Field(
        default=None,
        validation_alias="BACKEND_REDIS_URL",
    )
    REDIS_HOST: str = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "BACKEND_REDIS_HOST",
            "REDIS_HOST",
        ),
    )
    REDIS_PORT: int = Field(
        default=6379,
        validation_alias=AliasChoices(
            "BACKEND_REDIS_PORT",
            "REDIS_PORT",
        ),
    )
    REDIS_PASSWORD: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BACKEND_REDIS_PASSWORD",
            "REDIS_RUNTIME_PASSWORD",
            "REDIS_PASSWORD",
        ),
    )
    REDIS_DB: int = Field(
        default=0,
        validation_alias=AliasChoices(
            "BACKEND_REDIS_DB",
            "REDIS_DB",
        ),
    )
    REDIS_PREFIX: str = Field(
        default="web-app",
        min_length=1,
        validation_alias="BACKEND_REDIS_PREFIX",
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=20,
        ge=1,
        validation_alias="BACKEND_REDIS_MAX_CONNECTIONS",
    )
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_REDIS_SOCKET_CONNECT_TIMEOUT",
    )
    REDIS_SOCKET_TIMEOUT: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_REDIS_SOCKET_TIMEOUT",
    )
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(
        default=30,
        ge=0,
        validation_alias="BACKEND_REDIS_HEALTH_CHECK_INTERVAL",
    )

    @field_validator("API_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if value in {"", "/"}:
            return ""

        if not value.startswith("/"):
            raise ValueError("API prefix must start with '/'")

        if value.endswith("/"):
            raise ValueError("API prefix must not end with '/'")

        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        try:
            origins: object = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(_CORS_ORIGINS_FORMAT_ERROR) from error

        if not isinstance(origins, list):
            raise ValueError(_CORS_ORIGINS_FORMAT_ERROR)

        return origins

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        for origin in value:
            if (
                origin.username is not None
                or origin.password is not None
                or origin.path not in {None, "", "/"}
                or origin.query is not None
                or origin.fragment is not None
            ):
                raise ValueError("CORS origin must contain only a scheme, host, and optional port")

        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> PostgresDsn:
        if self.DATABASE_URL is not None:
            return self.DATABASE_URL

        return self._build_database_url(
            username=_POSTGRES_RUNTIME_USER,
            password=self.POSTGRES_PASSWORD,
        )

    @property
    def migration_database_url(self) -> PostgresDsn:
        if self.MIGRATION_DATABASE_URL is not None:
            return self.MIGRATION_DATABASE_URL

        if self.DATABASE_URL is not None:
            return self.DATABASE_URL

        if self.POSTGRES_MIGRATOR_PASSWORD is None:
            raise ValueError(
                "POSTGRES_MIGRATOR_PASSWORD is required when no migration database URL is set"
            )

        return self._build_database_url(
            username=_POSTGRES_MIGRATOR_USER,
            password=self.POSTGRES_MIGRATOR_PASSWORD,
        )

    def _build_database_url(self, *, username: str, password: SecretStr) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=username,
            password=password.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> RedisDsn:
        if self.REDIS_URL is not None:
            return self.REDIS_URL

        password = (
            self.REDIS_PASSWORD.get_secret_value() if self.REDIS_PASSWORD is not None else None
        )

        return RedisDsn.build(
            scheme="redis",
            username=_REDIS_RUNTIME_USER,
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            password=password or None,
            path=str(self.REDIS_DB),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.CORS_ORIGINS]

    def bootstrap_admin_password(self) -> str | None:
        password = (
            self.BOOTSTRAP_ADMIN_PASSWORD.get_secret_value()
            if self.BOOTSTRAP_ADMIN_PASSWORD
            else None
        )
        password_file = self.BOOTSTRAP_ADMIN_PASSWORD_FILE
        if password is not None and password_file is not None:
            raise ValueError(
                "Set only one of BACKEND_BOOTSTRAP_ADMIN_PASSWORD or "
                "BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE"
            )
        if password_file is not None:
            try:
                password = password_file.read_text(encoding="utf-8").rstrip("\r\n")
            except OSError as error:
                raise ValueError("Cannot read BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE") from error
        if password is not None and len(password) < 12:
            raise ValueError("BACKEND_BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters")
        return password


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
