"""The backend CLI as operators see it through ``otk``.

The host's ``otk`` (``infrastructure/cli/otk.py``) runs ``python -m app.otk`` in the
running API container. It offers only the commands that make sense there; commands
such as ``run`` and ``workers`` would start a second server or worker next to the
container's own. ``python -m app`` keeps the whole Litestar CLI for development.
"""

from __future__ import annotations

from importlib.metadata import version

import rich_click as click
from litestar.cli._utils import LitestarEnv, LitestarExtensionGroup
from litestar.cli.commands import core

from app.__main__ import setup_environment
from app.config import get_settings

COMMANDS = frozenset({"database", "info", "users", "version"})


class _OperatorGroup(LitestarExtensionGroup):
    """Hide the commands the app plugins add beyond ``COMMANDS``."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return [name for name in super().list_commands(ctx) if name in COMMANDS]

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        # Resolve first, so that aliases such as ``db`` still work.
        # Litestar picks the base class with a conditional import, so its type is unknown.
        command = super().get_command(ctx, cmd_name)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

        return command if command is not None and command.name in COMMANDS else None  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


@click.group(cls=_OperatorGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def otk_group(ctx: click.Context) -> None:
    """Administer the backend: users, database migrations and app information."""
    if ctx.obj is None:  # the app has not loaded yet; report why when a command needs it
        ctx.obj = lambda: LitestarEnv.from_env(None)


@click.command(name="version")
def version_command() -> None:
    """Show the backend release and the Litestar version."""
    # Litestar's own ``version`` shows only the framework, which tells an operator little.
    click.echo(f"Backend   {get_settings().app.version}")
    click.echo(f"Litestar  {version('litestar')}")


otk_group.add_command(core.info_command)  # pyright: ignore[reportArgumentType]
otk_group.add_command(version_command)


def run() -> None:
    setup_environment()
    otk_group(prog_name="otk")


if __name__ == "__main__":
    run()
