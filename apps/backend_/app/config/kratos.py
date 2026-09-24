from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KratosSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    public_url: str = Field(
        default="http://kratos:4433",
        validation_alias="BACKEND_KRATOS_PUBLIC_URL",
    )

    admin_url: str = Field(
        default="http://kratos:4434",
        validation_alias="BACKEND_KRATOS_ADMIN_URL",
    )

    session_cookie: str = Field(
        default="ory_kratos_session",
        min_length=1,
        validation_alias="BACKEND_KRATOS_SESSION_COOKIE",
    )

    public_timeout: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_KRATOS_PUBLIC_TIMEOUT",
    )

    admin_timeout: float = Field(
        default=10.0,
        gt=0,
        validation_alias="BACKEND_KRATOS_ADMIN_TIMEOUT",
    )

    public_concurrency: int = Field(
        default=20,
        ge=1,
        validation_alias="BACKEND_KRATOS_PUBLIC_CONCURRENCY",
    )

    admin_concurrency: int = Field(
        default=4,
        ge=1,
        validation_alias="BACKEND_KRATOS_ADMIN_CONCURRENCY",
    )


@lru_cache
def get_kratos_settings() -> KratosSettings:
    return KratosSettings()
