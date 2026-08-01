import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.unit
def test_api_prefix_is_empty_by_default() -> None:
    assert Settings().API_PREFIX == ""


@pytest.mark.unit
@pytest.mark.parametrize(
    ("api_prefix", "expected_prefix"),
    [
        pytest.param("/api", "/api", id="single-segment"),
        pytest.param("/internal/api", "/internal/api", id="multiple-segments"),
        pytest.param("/", "", id="root"),
        pytest.param("", "", id="empty"),
    ],
)
def test_api_prefix_accepts_valid_path(api_prefix: str, expected_prefix: str) -> None:
    settings = Settings.model_validate({"BACKEND_API_PREFIX": api_prefix})

    assert settings.API_PREFIX == expected_prefix


@pytest.mark.unit
@pytest.mark.parametrize(
    "api_prefix",
    [
        pytest.param("api", id="missing-leading-slash"),
        pytest.param("/api/", id="trailing-slash"),
    ],
)
def test_api_prefix_rejects_invalid_path(api_prefix: str) -> None:
    with pytest.raises(ValidationError, match="API prefix must"):
        Settings.model_validate({"BACKEND_API_PREFIX": api_prefix})
