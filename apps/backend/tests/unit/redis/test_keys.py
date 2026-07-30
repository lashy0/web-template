import pytest

from app.core.config import Settings
from app.redis.keys import build_redis_key


@pytest.mark.unit
def test_build_redis_key() -> None:
    settings = Settings.model_validate(
        {"BACKEND_REDIS_PREFIX": "web-app"},
    )

    result = build_redis_key(
        settings,
        "users",
        42,
    )

    assert result == "web-app:users:42"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("prefix", "parts"),
    [
        pytest.param(":", ("users", 42), id="empty-prefix"),
        pytest.param("web-app", (), id="missing-parts"),
        pytest.param("web-app", ("users", ""), id="empty-part"),
    ],
)
def test_build_redis_key_rejects_invalid_values(
    prefix: str,
    parts: tuple[str | int, ...],
) -> None:
    settings = Settings.model_validate(
        {"BACKEND_REDIS_PREFIX": prefix},
    )

    with pytest.raises(ValueError):
        build_redis_key(settings, *parts)
