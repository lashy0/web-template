from dataclasses import dataclass, field
from functools import lru_cache

from advanced_alchemy.utils.text import slugify
from litestar.config.cors import CORSConfig
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.database import DatabaseSettings
from app.config.hydra import HydraSettings
from app.config.kratos import KratosSettings
from app.config.log import LogSettings
from app.config.queue import QueueSettings
from app.config.redis import RedisSettings
from app.config.verification import VerificationSettings


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    name: str = Field(
        default="Backend",
        validation_alias="APP_NAME",
    )

    debug: bool = Field(
        default=False,
        validation_alias="LITESTAR_DEBUG",
    )

    allowed_cors_origins: list[str] = Field(
        default=["*"],
        validation_alias="ALLOWED_CORS_ORIGINS",
    )

    @property
    def slug(self) -> str:
        return slugify(self.name)

    def get_cors_config(self) -> CORSConfig:
        return CORSConfig(
            allow_origins=self.allowed_cors_origins,
        )


@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    hydra: HydraSettings = field(default_factory=HydraSettings)
    kratos: KratosSettings = field(default_factory=KratosSettings)
    log: LogSettings = field(default_factory=LogSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    queue: QueueSettings = field(default_factory=QueueSettings)
    verification: VerificationSettings = field(default_factory=VerificationSettings)


@lru_cache
def get_settings() -> Settings:
    """Settings from the environment; the application default when none are passed."""
    return Settings()
