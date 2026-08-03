# /// script
# requires-python = ">=3.13,<4"
# dependencies = ["typer>=0.27.0,<1.0.0"]
# ///

import shutil
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    help="Manage Traefik.",
    no_args_is_help=True,
    add_completion=False,
)

TRAEFIK_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = TRAEFIK_ROOT.parent.parent
TRAEFIK_NETWORK = "traefik-public"


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


COMPOSE_FILES = {
    Environment.DEV: (
        TRAEFIK_ROOT / "docker-compose.yaml",
        TRAEFIK_ROOT / "docker-compose.dev.yaml",
    ),
    Environment.PROD: (
        TRAEFIK_ROOT / "docker-compose.yaml",
        TRAEFIK_ROOT / "docker-compose.prod.yaml",
    ),
}


class DeploymentError(RuntimeError):
    pass


def get_docker() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise DeploymentError("Docker CLI is not installed or is not available on PATH")
    return docker


def compose_command(docker: str, environment: Environment) -> list[str]:
    command = [
        docker,
        "compose",
        "--env-file",
        str(REPOSITORY_ROOT / ".env"),
        "--env-file",
        str(TRAEFIK_ROOT / ".env"),
    ]
    for compose_file in COMPOSE_FILES[environment]:
        command.extend(("-f", str(compose_file)))
    return command


def validate_compose(command: list[str]) -> None:
    result = subprocess.run(
        [*command, "config", "--quiet"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DeploymentError(result.stderr.strip() or "Docker Compose configuration is invalid")
    if result.stderr:
        typer.secho(result.stderr.rstrip(), fg=typer.colors.YELLOW, err=True)


def ensure_traefik_network(docker: str) -> None:
    result = subprocess.run(
        [docker, "network", "inspect", TRAEFIK_NETWORK],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            [docker, "network", "create", TRAEFIK_NETWORK],
            check=True,
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
    docker = get_docker()
    command = compose_command(docker, environment)
    validate_compose(command)
    ensure_traefik_network(docker)

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
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)
    typer.secho("Traefik is running.", fg=typer.colors.GREEN, bold=True, err=True)


@app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to inspect: dev or prod."),
    ],
) -> None:
    """Show the current state and published ports of Traefik."""
    docker = get_docker()
    command = compose_command(docker, environment)
    validate_compose(command)
    subprocess.run(
        [*command, "ps"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop Traefik while keeping its external network and persistent data."""
    docker = get_docker()
    command = compose_command(docker, environment)
    validate_compose(command)
    typer.secho(
        f"Stopping Traefik ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    subprocess.run(
        [*command, "down"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    typer.secho("Traefik is stopped.", fg=typer.colors.GREEN, bold=True, err=True)


def main() -> None:
    try:
        app()
    except DeploymentError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, bold=True, err=True)
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        if error.stderr:
            typer.secho(error.stderr.rstrip(), fg=typer.colors.RED, err=True)
        else:
            typer.secho(
                f"Error: command failed with exit code {error.returncode}.",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
        raise SystemExit(error.returncode) from None


if __name__ == "__main__":
    main()
