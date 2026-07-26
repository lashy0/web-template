from functools import lru_cache
from typing import Annotated, Any

from pydantic import (
    AnyUrl,
    BeforeValidator,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    computed_field,
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
        default="/api",
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
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr = SecretStr("")
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "backend"

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
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: SecretStr | None = None
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> PostgresDsn:
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
        password = (
            self.REDIS_PASSWORD.get_secret_value()
            if self.REDIS_PASSWORD is not None
            else None
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
        return [
            str(origin).rstrip("/") for origin in self.CORS_ORIGINS
        ] + [
            self.FRONTEND_HOST
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
