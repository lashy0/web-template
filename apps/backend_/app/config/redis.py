from pydantic import AliasChoices, Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_REDIS_RUNTIME_USER = "otk_app_runtime"


class RedisSettings(BaseSettings):
    """Redis connection shared by the task queue and, later, realtime channels.

    The runtime ACL user may only touch this application's keys: the ``prefix``
    namespace and the SAQ keys of the queue named after it.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    redis_url_override: RedisDsn | None = Field(
        default=None,
        validation_alias="REDIS_URL",
    )

    host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("BACKEND_REDIS_HOST", "REDIS_HOST"),
    )

    port: int = Field(
        default=6379,
        validation_alias=AliasChoices("BACKEND_REDIS_PORT", "REDIS_PORT"),
    )

    db: int = Field(
        default=0,
        validation_alias=AliasChoices("BACKEND_REDIS_DB", "REDIS_DB"),
    )

    runtime_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("BACKEND_REDIS_PASSWORD", "REDIS_RUNTIME_PASSWORD"),
    )

    prefix: str = Field(
        default="otk-app",
        min_length=1,
        pattern=r"^[a-z0-9-]+$",
        validation_alias="BACKEND_REDIS_PREFIX",
    )

    @property
    def url(self) -> RedisDsn:
        if self.redis_url_override is not None:
            return self.redis_url_override

        if self.runtime_password is None:
            raise ValueError("BACKEND_REDIS_PASSWORD is required when REDIS_URL is not set")

        return RedisDsn.build(
            scheme="redis",
            username=_REDIS_RUNTIME_USER,
            password=self.runtime_password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=str(self.db),
        )
