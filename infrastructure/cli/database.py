from typing import Annotated

import typer

from cli.compose import (
    INFRASTRUCTURE_ROOT,
    ComposeProject,
    Environment,
    ensure_network,
    find_tool,
    run_cli,
    run_command,
)

DATABASE_NETWORK = "web-database"
PROJECT = ComposeProject(INFRASTRUCTURE_ROOT / "database")

app = typer.Typer(
    help="Manage the Web App database infrastructure.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration: dev or prod."),
    ],
) -> None:
    """Start the database containers and wait until they are healthy."""
    docker = find_tool("docker")
    ensure_network(docker, DATABASE_NETWORK, internal=True)
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "up", "--detach", "--wait"])


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration: dev or prod."),
    ],
) -> None:
    """Stop the database containers while preserving their volumes."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "down"])


@app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration: dev or prod."),
    ],
) -> None:
    """Show the database containers reported by Docker Compose."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "ps"])


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
