import pytest
from pydantic import PostgresDsn, SecretStr

from app.core.config import Settings


@pytest.mark.unit
def test_explicit_database_url_takes_precedence_for_runtime_and_migrations() -> None:
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
    assert settings.migration_database_url == explicit_url


@pytest.mark.unit
def test_explicit_migration_database_url_takes_precedence() -> None:
    runtime_url = PostgresDsn("postgresql+psycopg://runtime:secret@db.example.com:5432/app")
    migration_url = PostgresDsn("postgresql+psycopg://migrator:secret@db.example.com:5432/app")
    settings = Settings.model_validate(
        {
            "BACKEND_DATABASE_URL": runtime_url,
            "BACKEND_MIGRATION_DATABASE_URL": migration_url,
        }
    )

    assert settings.database_url == runtime_url
    assert settings.migration_database_url == migration_url


@pytest.mark.unit
def test_database_url_is_built_from_backend_connection_fields() -> None:
    settings = Settings.model_validate(
        {
            "BACKEND_POSTGRES_HOST": "postgres.internal",
            "BACKEND_POSTGRES_PORT": 5433,
            "BACKEND_POSTGRES_PASSWORD": SecretStr("secret"),
            "BACKEND_POSTGRES_DB": "app_db",
        }
    )

    assert (
        str(settings.database_url)
        == "postgresql+psycopg://web_app_runtime:secret@postgres.internal:5433/app_db"
    )


@pytest.mark.unit
def test_legacy_postgres_connection_fields_are_supported() -> None:
    settings = Settings.model_validate(
        {
            "POSTGRES_HOST": "postgres.internal",
            "POSTGRES_PORT": 5432,
            "POSTGRES_PASSWORD": SecretStr(""),
            "POSTGRES_DB": "app_db",
        }
    )

    assert (
        str(settings.database_url)
        == "postgresql+psycopg://web_app_runtime@postgres.internal:5432/app_db"
    )


@pytest.mark.unit
def test_runtime_password_from_shared_environment_is_supported() -> None:
    settings = Settings.model_validate(
        {
            "POSTGRES_RUNTIME_PASSWORD": SecretStr("runtime-secret"),
        }
    )

    assert settings.POSTGRES_PASSWORD == SecretStr("runtime-secret")


@pytest.mark.unit
def test_migration_database_url_uses_the_migrator_credentials() -> None:
    settings = Settings.model_validate(
        {
            "POSTGRES_HOST": "postgres.internal",
            "POSTGRES_PORT": 5433,
            "POSTGRES_DB": "app_db",
            "POSTGRES_RUNTIME_PASSWORD": SecretStr("runtime-secret"),
            "POSTGRES_MIGRATOR_PASSWORD": SecretStr("migrator-secret"),
        }
    )

    assert (
        str(settings.migration_database_url)
        == "postgresql+psycopg://web_app_migrator:migrator-secret@postgres.internal:5433/app_db"
    )


@pytest.mark.unit
def test_migration_database_url_requires_the_migrator_password() -> None:
    settings = Settings.model_validate(
        {
            "POSTGRES_MIGRATOR_PASSWORD": None,
        }
    )

    with pytest.raises(ValueError, match="POSTGRES_MIGRATOR_PASSWORD is required"):
        _ = settings.migration_database_url
