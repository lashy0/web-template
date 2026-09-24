from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class HydraSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    public_url: str = Field(
        default="http://hydra:4444",
        validation_alias="BACKEND_HYDRA_PUBLIC_URL",
    )
    admin_url: str = Field(
        default="http://hydra:4445",
        validation_alias="BACKEND_HYDRA_ADMIN_URL",
    )
    public_timeout: float = Field(
        default=2.0,
        gt=0,
        validation_alias="BACKEND_HYDRA_PUBLIC_TIMEOUT",
    )
    admin_timeout: float = Field(
        default=10.0,
        gt=0,
        validation_alias="BACKEND_HYDRA_ADMIN_TIMEOUT",
    )
    admin_concurrency: int = Field(
        default=4,
        ge=1,
        validation_alias="BACKEND_HYDRA_ADMIN_CONCURRENCY",
    )
    pak_access_key_encryption_key: SecretStr | None = Field(
        default=None,
        validation_alias="BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY",
    )


@lru_cache
def get_hydra_settings() -> HydraSettings:
    return HydraSettings()
