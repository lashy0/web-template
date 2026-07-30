import pytest
from pydantic import PostgresDsn, SecretStr

from app.core.config import Settings


@pytest.mark.unit
def test_explicit_database_url_takes_precedence() -> None:
    explicit_url = PostgresDsn("postgresql+psycopg://user:secret@db.example.com:5432/app")
    settings = Settings.model_validate(
        {
            "BACKEND_DATABASE_URL": explicit_url,
            "BACKEND_POSTGRES_HOST": "ignored",
            "BACKEND_POSTGRES_PORT": 1234,
            "BACKEND_POSTGRES_DB": "ignored",
        }
    )

    assert settings.database_url == explicit_url


@pytest.mark.unit
def test_database_url_is_built_from_backend_connection_fields() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_POSTGRES_HOST": "postgres.internal",
            "BACKEND_POSTGRES_PORT": 5433,
            "BACKEND_POSTGRES_USER": "app",
            "BACKEND_POSTGRES_PASSWORD": SecretStr("secret"),
            "BACKEND_POSTGRES_DB": "app_db",
        }
    )

    assert (
        str(settings.database_url)
        == "postgresql+psycopg://app:secret@postgres.internal:5433/app_db"
    )


@pytest.mark.unit
def test_legacy_postgres_connection_fields_are_supported() -> None:
    settings = Settings.model_validate(
        {
            "POSTGRES_HOST": "postgres.internal",
            "POSTGRES_PORT": 5432,
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": SecretStr(""),
            "POSTGRES_DB": "app_db",
        }
    )

    assert (
        str(settings.database_url) == "postgresql+psycopg://postgres@postgres.internal:5432/app_db"
    )
