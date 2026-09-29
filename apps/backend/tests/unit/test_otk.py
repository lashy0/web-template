from collections.abc import Iterator

import pytest
import rich_click as click
from click.testing import CliRunner

from app.config import get_settings
from app.otk import otk_group

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _litestar_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the app as ``python -m app.otk`` does; the group loads it to list the plugin commands."""
    monkeypatch.setenv("LITESTAR_APP", "app.server.asgi:create_app")


@pytest.fixture
def context() -> Iterator[click.Context]:
    with otk_group.make_context("otk", ["version"]) as context:
        yield context


def test_otk_lists_only_operator_commands(context: click.Context) -> None:
    assert otk_group.list_commands(context) == ["database", "info", "users", "version"]


def test_otk_hides_commands_of_plugins(context: click.Context) -> None:
    assert otk_group.get_command(context, "workers") is None


def test_otk_resolves_command_aliases(context: click.Context) -> None:
    command = otk_group.get_command(context, "db")

    assert command is not None
    assert command.name == "database"


@pytest.fixture
def release(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("BACKEND_VERSION", "2026.9.1")
    get_settings.cache_clear()

    yield "2026.9.1"

    get_settings.cache_clear()


def test_otk_version_shows_the_backend_release(release: str) -> None:
    result = CliRunner().invoke(otk_group, ["version"])

    assert result.exit_code == 0
    assert release in result.output
