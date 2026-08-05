from typing import Annotated

import typer

from cli.compose import (
    INFRASTRUCTURE_ROOT,
    ROOT_ENV_FILE,
    ComposeProject,
    Environment,
    ensure_network,
    find_tool,
    run_cli,
    run_command,
)

TRAEFIK_ROOT = INFRASTRUCTURE_ROOT / "traefik"
TRAEFIK_NETWORK = "traefik-public"
PROJECT = ComposeProject(TRAEFIK_ROOT, (ROOT_ENV_FILE, TRAEFIK_ROOT / ".env"))

app = typer.Typer(
    help="Manage Traefik.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to use: dev or prod."),
    ],
    health_timeout: Annotated[
        int,
        typer.Option(min=1, help="Seconds to wait until Traefik is healthy."),
    ] = 60,
) -> None:
    """Start or update Traefik and wait until it is healthy."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    ensure_network(docker, TRAEFIK_NETWORK)
    command.extend(
        (
            "up",
            "--detach",
            "--pull",
            "always",
            "--wait",
            "--wait-timeout",
            str(health_timeout),
        )
    )

    typer.secho(
        f"Deploying Traefik ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command(command)
    typer.secho("Traefik is running.", fg=typer.colors.GREEN, bold=True, err=True)


@app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to inspect: dev or prod."),
    ],
) -> None:
    """Show the current state and published ports of Traefik."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "ps"])


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop Traefik while keeping its external network and persistent data."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    typer.secho(
        f"Stopping Traefik ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command([*command, "down"])
    typer.secho("Traefik is stopped.", fg=typer.colors.GREEN, bold=True, err=True)


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
