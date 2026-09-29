from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QueueSettings(BaseSettings):
    """How background task workers run."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    workers_in_server: bool = Field(
        default=False,
        validation_alias="BACKEND_WORKERS_IN_SERVER",
        description=(
            "Start worker processes together with `litestar run`, for development. "
            "Deployments run `litestar workers run` as a service of its own."
        ),
    )
