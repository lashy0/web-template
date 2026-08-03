# /// script
# requires-python = ">=3.13,<4"
# dependencies = ["typer>=0.27.0,<1.0.0"]
# ///

import os
import shutil
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    help="Manage the application.",
    no_args_is_help=True,
    add_completion=False,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPOSITORY_ROOT / "apps/backend"
TRAEFIK_NETWORK = "traefik-public"


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


COMPOSE_FILES = {
    Environment.DEV: (
        REPOSITORY_ROOT / "docker-compose.yaml",
        REPOSITORY_ROOT / "docker-compose.dev.yaml",
    ),
    Environment.PROD: (
        REPOSITORY_ROOT / "docker-compose.yaml",
        REPOSITORY_ROOT / "docker-compose.prod.yaml",
    ),
}


class DeploymentError(RuntimeError):
    pass


def get_tool(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise DeploymentError(f"{name} is not installed or is not available on PATH")
    return executable


def require_traefik_network(docker: str) -> None:
    result = subprocess.run(
        [docker, "network", "inspect", TRAEFIK_NETWORK],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DeploymentError(
            f"Required Docker network '{TRAEFIK_NETWORK}' does not exist. "
            "Deploy Traefik infrastructure first."
        )


def compose_command(docker: str, environment: Environment) -> list[str]:
    command = [docker, "compose"]
    for compose_file in COMPOSE_FILES[environment]:
        command.extend(("-f", str(compose_file)))
    return command


def validate_compose(
    command: list[str],
    command_environment: dict[str, str],
) -> None:
    result = subprocess.run(
        [*command, "config", "--quiet"],
        cwd=REPOSITORY_ROOT,
        env=command_environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DeploymentError(result.stderr.strip() or "Docker Compose configuration is invalid")
    if result.stderr:
        typer.secho(result.stderr.rstrip(), fg=typer.colors.YELLOW, err=True)


def read_backend_version(uv: str) -> str:
    result = subprocess.run(
        [uv, "version", "--project", str(BACKEND_ROOT), "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip()
    if not version:
        raise DeploymentError(f"Project version is missing in {BACKEND_ROOT / 'pyproject.toml'}")
    return version


def read_git_sha(git: str) -> str:
    result = subprocess.run(
        [git, "rev-parse", "--short", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    git_sha = result.stdout.strip()
    if not git_sha:
        raise DeploymentError("Git SHA is missing")
    return git_sha


def command_environment(environment: Environment) -> dict[str, str]:
    values = os.environ.copy()
    version = read_backend_version(get_tool("uv"))
    values["BACKEND_VERSION"] = version
    if environment is Environment.PROD:
        values["TAG"] = f"{version}-{read_git_sha(get_tool('git'))}"
    return values


@app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to start: dev or prod."),
    ],
) -> None:
    """Build and start the application services."""
    docker = get_tool("docker")
    command = compose_command(docker, environment)
    values = command_environment(environment)
    validate_compose(command, values)
    require_traefik_network(docker)

    if environment is Environment.DEV:
        message = "Starting the development environment"
        arguments = ("up", "--build", "--watch")
    else:
        message = f"Deploying web-app-backend:{values['TAG']}"
        arguments = ("up", "--detach", "--build")

    typer.secho(message, fg=typer.colors.CYAN, bold=True, err=True)
    subprocess.run(
        [*command, *arguments],
        cwd=REPOSITORY_ROOT,
        env=values,
        check=True,
    )
    if environment is Environment.PROD:
        typer.secho("Production is running.", fg=typer.colors.GREEN, bold=True, err=True)


@app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to inspect: dev or prod."),
    ],
) -> None:
    """Show the current state and published ports of the services."""
    docker = get_tool("docker")
    command = compose_command(docker, environment)
    values = command_environment(environment)
    validate_compose(command, values)
    subprocess.run(
        [*command, "ps"],
        cwd=REPOSITORY_ROOT,
        env=values,
        check=True,
    )


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop and remove the application services."""
    docker = get_tool("docker")
    command = compose_command(docker, environment)
    values = command_environment(environment)
    validate_compose(command, values)

    typer.secho(
        f"Stopping the application ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    subprocess.run(
        [*command, "down"],
        cwd=REPOSITORY_ROOT,
        env=values,
        check=True,
    )
    typer.secho("Application is stopped.", fg=typer.colors.GREEN, bold=True, err=True)


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
