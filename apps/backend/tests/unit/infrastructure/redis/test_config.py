import pytest
from pydantic import RedisDsn, SecretStr

from app.core.config import Settings


@pytest.mark.unit
def test_explicit_redis_url_takes_precedence() -> None:
    explicit_url = RedisDsn("rediss://user:secret@redis.example.com:6380/5")
    settings = Settings.model_validate(
        {
            "BACKEND_REDIS_URL": explicit_url,
            "BACKEND_REDIS_HOST": "ignored",
            "BACKEND_REDIS_PORT": 1234,
            "BACKEND_REDIS_DB": 9,
        }
    )

    assert settings.redis_url == explicit_url


@pytest.mark.unit
def test_redis_url_is_built_from_connection_fields() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_REDIS_URL": None,
            "BACKEND_REDIS_HOST": "redis.internal",
            "BACKEND_REDIS_PORT": 6380,
            "BACKEND_REDIS_PASSWORD": SecretStr("secret"),
            "BACKEND_REDIS_DB": 2,
        }
    )

    assert settings.redis_url.scheme == "redis"
    assert settings.redis_url.host == "redis.internal"
    assert settings.redis_url.port == 6380
    assert settings.redis_url.username == "web_app_runtime"
    assert settings.redis_url.password == "secret"
    assert settings.redis_url.path == "/2"


@pytest.mark.unit
def test_generic_redis_connection_fields_are_supported() -> None:
    settings = Settings.model_validate(
        {
            "REDIS_HOST": "redis.generic",
            "REDIS_PORT": 6381,
            "REDIS_PASSWORD": SecretStr("generic-secret"),
            "REDIS_DB": 3,
        }
    )

    assert settings.REDIS_HOST == "redis.generic"
    assert settings.REDIS_PORT == 6381
    assert settings.REDIS_PASSWORD == SecretStr("generic-secret")
    assert settings.REDIS_DB == 3


@pytest.mark.unit
def test_backend_redis_connection_fields_take_precedence() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_REDIS_HOST": "redis.backend",
            "REDIS_HOST": "redis.generic",
            "BACKEND_REDIS_PORT": 6382,
            "REDIS_PORT": 6381,
            "BACKEND_REDIS_PASSWORD": SecretStr("backend-secret"),
            "REDIS_PASSWORD": SecretStr("generic-secret"),
            "BACKEND_REDIS_DB": 4,
            "REDIS_DB": 3,
        }
    )

    assert settings.REDIS_HOST == "redis.backend"
    assert settings.REDIS_PORT == 6382
    assert settings.REDIS_PASSWORD == SecretStr("backend-secret")
    assert settings.REDIS_DB == 4


@pytest.mark.unit
def test_runtime_password_from_shared_environment_is_supported() -> None:
    settings = Settings.model_validate(
        {
            "REDIS_RUNTIME_PASSWORD": SecretStr("runtime-secret"),
        }
    )

    assert settings.REDIS_PASSWORD == SecretStr("runtime-secret")
    assert settings.redis_url.username == "web_app_runtime"
