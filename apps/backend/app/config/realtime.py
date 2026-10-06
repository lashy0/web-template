from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RealtimeSettings(BaseSettings):
    """How realtime events reach the API processes that stream them to browsers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    backend: Literal["redis", "memory"] = Field(
        default="redis",
        validation_alias="BACKEND_REALTIME_BACKEND",
        description=(
            "`redis` carries events between the API and worker processes over Redis pub/sub. "
            "`memory` keeps them inside one process, for tests."
        ),
    )
