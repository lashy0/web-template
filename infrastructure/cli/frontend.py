import json
import os
from typing import Annotated

import typer

from cli.compose import (
    INFRASTRUCTURE_ROOT,
    REPOSITORY_ROOT,
    ComposeProject,
    DeploymentError,
    Environment,
    find_tool,
    require_network,
    run_command,
)

FRONTEND_ROOT = INFRASTRUCTURE_ROOT / "frontend"
FRONTEND_PACKAGE = REPOSITORY_ROOT / "apps" / "frontend" / "package.json"
TRAEFIK_NETWORK = "traefik-public"
PROJECT = ComposeProject(FRONTEND_ROOT)

frontend_app = typer.Typer(
    help="Manage the frontend.",
    no_args_is_help=True,
    add_completion=False,
)


def read_frontend_version() -> str:
    try:
        package = json.loads(FRONTEND_PACKAGE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeploymentError(f"Unable to read {FRONTEND_PACKAGE}") from error

    version = package.get("version")
    if not isinstance(version, str) or not version:
        raise DeploymentError(f"Project version is missing in {FRONTEND_PACKAGE}")
    return version


def command_environment(environment: Environment) -> dict[str, str]:
    values = os.environ.copy()
    if environment is Environment.PROD:
        git = find_tool("git")
        values["FRONTEND_TAG"] = f"{read_frontend_version()}-{read_git_sha(git)}"
    return values


def read_git_sha(git: str) -> str:
    result = run_command([git, "rev-parse", "--short", "HEAD"], capture_output=True)
    git_sha = result.stdout.strip()
    if not git_sha:
        raise DeploymentError("Git SHA is missing")
    return git_sha


@frontend_app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to start: dev or prod."),
    ],
) -> None:
    """Build and start the frontend."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    require_network(docker, TRAEFIK_NETWORK, "Deploy Traefik infrastructure first.")
    arguments: tuple[str, ...]

    if environment is Environment.DEV:
        message = "Starting the frontend development environment"
        arguments = ("up", "--build")
    else:
        message = f"Deploying frontend release {values['FRONTEND_TAG']}"
        arguments = ("up", "--detach", "--build")

    typer.secho(message, fg=typer.colors.CYAN, bold=True, err=True)
    run_command([*command, *arguments], process_environment=values)
    if environment is Environment.PROD:
        typer.secho("Frontend is running.", fg=typer.colors.GREEN, bold=True, err=True)


@frontend_app.command()
def status(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to inspect: dev or prod."),
    ],
) -> None:
    """Show the frontend state and published ports."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    run_command([*command, "ps"], process_environment=values)


@frontend_app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop and remove the frontend."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    typer.secho(
        f"Stopping the frontend ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command([*command, "down"], process_environment=values)
    typer.secho("Frontend is stopped.", fg=typer.colors.GREEN, bold=True, err=True)

