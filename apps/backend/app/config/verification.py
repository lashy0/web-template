from datetime import timedelta
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VerificationSettings(BaseSettings):
    """When a verification session that the PAK stopped reporting is closed."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    reopen_inactivity_minutes: int = Field(
        default=60,
        ge=1,
        validation_alias="BACKEND_VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES",
        description="A KG unit may start a new session elsewhere once its running one is this idle.",
    )

    session_ttl_minutes: int = Field(
        default=120,
        ge=1,
        validation_alias="BACKEND_VERIFICATION_SESSION_TTL_MINUTES",
        description="The background sweep closes a running session this idle as incomplete.",
    )

    @model_validator(mode="after")
    def _reopen_before_ttl(self) -> Self:
        if self.reopen_inactivity_minutes >= self.session_ttl_minutes:
            msg = (
                "BACKEND_VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES must be less than "
                "BACKEND_VERIFICATION_SESSION_TTL_MINUTES"
            )
            raise ValueError(msg)

        return self

    @property
    def reopen_inactivity(self) -> timedelta:
        return timedelta(minutes=self.reopen_inactivity_minutes)

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(minutes=self.session_ttl_minutes)
