from typing import Annotated

import typer

from cli.compose import (
    INFRASTRUCTURE_ROOT,
    ROOT_ENV_FILE,
    ComposeProject,
    Environment,
    ensure_network,
    find_tool,
    require_network,
    run_cli,
    run_command,
)

IDENTITY_ROOT = INFRASTRUCTURE_ROOT / "identity"
IDENTITY_NETWORK = "web-identity"
DATABASE_NETWORK = "web-database"
TRAEFIK_NETWORK = "traefik-public"
PROJECT = ComposeProject(IDENTITY_ROOT, (ROOT_ENV_FILE, IDENTITY_ROOT / ".env"))

app = typer.Typer(
    help="Manage the Ory Kratos and Hydra identity infrastructure.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to start: dev or prod."),
    ],
    health_timeout: Annotated[
        int,
        typer.Option(min=1, help="Seconds to wait until Kratos and Hydra are healthy."),
    ] = 90,
) -> None:
    """Run migrations, start Kratos and Hydra, and wait until both are healthy."""
    docker = find_tool("docker")
    require_network(docker, DATABASE_NETWORK, "Start database infrastructure first.")
    require_network(docker, TRAEFIK_NETWORK, "Start Traefik infrastructure first.")
    ensure_network(docker, IDENTITY_NETWORK)
    command = PROJECT.prepare(docker, environment)

    typer.secho(
        f"Deploying identity infrastructure ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command(
        [
            *command,
            "up",
            "--detach",
            "--pull",
            "always",
            "--wait",
            "--wait-timeout",
            str(health_timeout),
        ]
    )
    typer.secho("Kratos and Hydra are healthy.", fg=typer.colors.GREEN, bold=True, err=True)


@app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to inspect: dev or prod."),
    ],
) -> None:
    """Show migration, Kratos, and Hydra containers reported by Compose."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "ps", "--all"])


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop Kratos and Hydra while preserving their external network and databases."""
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    typer.secho(
        f"Stopping identity infrastructure ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command([*command, "down"])
    typer.secho("Identity infrastructure is stopped.", fg=typer.colors.GREEN, bold=True, err=True)


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
