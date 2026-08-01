from functools import lru_cache
from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    AnyUrl,
    BeforeValidator,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]

    if isinstance(v, list | str):
        return v

    raise ValueError(v)


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

    # Frontend / CORS
    FRONTEND_HOST: str = "http://localhost:5173"

    CORS_ORIGINS: Annotated[
        list[AnyUrl] | str,
        BeforeValidator(parse_cors),
    ] = Field(
        default=[],
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    # Postgres
    DATABASE_URL: PostgresDsn | None = Field(
        default=None,
        validation_alias="BACKEND_DATABASE_URL",
    )
    POSTGRES_USER: str = Field(
        default="postgres",
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_USER",
            "POSTGRES_USER",
        ),
    )
    POSTGRES_PASSWORD: SecretStr = Field(
        default=SecretStr("changepassword"),
        validation_alias=AliasChoices(
            "BACKEND_POSTGRES_PASSWORD",
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> PostgresDsn:
        if self.DATABASE_URL is not None:
            return self.DATABASE_URL

        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
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
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            password=password or None,
            path=str(self.REDIS_DB),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.CORS_ORIGINS] + [self.FRONTEND_HOST]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
