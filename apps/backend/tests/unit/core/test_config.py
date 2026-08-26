from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.unit
def test_readiness_timeout_is_parsed_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_READINESS_TIMEOUT", "1.5")

    assert Settings().READINESS_TIMEOUT == 1.5


@pytest.mark.unit
def test_readiness_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"BACKEND_READINESS_TIMEOUT": 0})


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


@pytest.mark.unit
def test_cors_origins_are_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)

    settings = Settings()

    assert settings.all_cors_origins == []


@pytest.mark.unit
def test_cors_origins_accept_url_list() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_CORS_ORIGINS": [
                "https://app.example.com",
                "https://admin.example.com/",
            ],
        }
    )

    assert settings.all_cors_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


@pytest.mark.unit
def test_cors_origins_reject_non_http_urls() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"BACKEND_CORS_ORIGINS": ["ftp://files.example.com"]})


@pytest.mark.unit
def test_cors_origins_are_parsed_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        '["https://app.example.com", "http://localhost:5173"]',
    )

    settings = Settings()

    assert settings.all_cors_origins == ["https://app.example.com", "http://localhost:5173"]


@pytest.mark.unit
def test_cors_origins_report_the_expected_environment_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "[http://localhost]")

    with pytest.raises(
        ValidationError,
        match=r"BACKEND_CORS_ORIGINS must be a JSON array.*http://localhost:5173",
    ):
        Settings()


@pytest.mark.unit
def test_bootstrap_password_accepts_one_environment_secret() -> None:
    settings = Settings.model_validate(
        {"BACKEND_BOOTSTRAP_ADMIN_PASSWORD": "correct-horse-battery-staple"}
    )

    assert settings.bootstrap_admin_password() == "correct-horse-battery-staple"


@pytest.mark.unit
def test_bootstrap_password_rejects_two_sources() -> None:
    password_file = Path("bootstrap-password")
    settings = Settings.model_validate(
        {
            "BACKEND_BOOTSTRAP_ADMIN_PASSWORD": "correct-horse-battery-staple",
            "BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE": password_file,
        }
    )

    with pytest.raises(ValueError, match="Set only one"):
        settings.bootstrap_admin_password()


@pytest.mark.unit
def test_bootstrap_password_reads_a_secret_file_without_its_final_newline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password_file = Path("bootstrap-password")
    monkeypatch.setattr(
        Path, "read_text", lambda *_args, **_kwargs: "correct-horse-battery-staple\n"
    )
    settings = Settings.model_validate({"BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE": password_file})

    assert settings.bootstrap_admin_password() == "correct-horse-battery-staple"


@pytest.mark.unit
@pytest.mark.parametrize(
    "cors_origin",
    [
        pytest.param("https://user@app.example.com", id="userinfo"),
        pytest.param("https://app.example.com/api", id="path"),
        pytest.param("https://app.example.com?tenant=one", id="query"),
        pytest.param("https://app.example.com#fragment", id="fragment"),
    ],
)
def test_cors_origins_reject_non_origin_url_components(cors_origin: str) -> None:
    with pytest.raises(ValidationError, match="must contain only"):
        Settings.model_validate({"BACKEND_CORS_ORIGINS": [cors_origin]})
