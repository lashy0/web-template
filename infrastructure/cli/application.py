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
    network_exists,
    run_cli,
    run_command,
)

APPLICATION_ROOT = INFRASTRUCTURE_ROOT / "application"
BACKEND_ROOT = REPOSITORY_ROOT / "apps/backend"
TRAEFIK_NETWORK = "traefik-public"
DATABASE_NETWORK = "web-database"
DATABASE_PROJECT = "web-database"
PROJECT = ComposeProject(APPLICATION_ROOT)

app = typer.Typer(
    help="Manage the application.",
    no_args_is_help=True,
    add_completion=False,
)


def require_traefik_network(docker: str) -> None:
    if not network_exists(docker, TRAEFIK_NETWORK):
        raise DeploymentError(
            f"Required Docker network '{TRAEFIK_NETWORK}' does not exist. "
            "Deploy Traefik infrastructure first."
        )


def require_database_stack(docker: str) -> None:
    if not network_exists(docker, DATABASE_NETWORK):
        raise DeploymentError(
            f"Required Docker network '{DATABASE_NETWORK}' does not exist. "
            "Start database infrastructure first."
        )

    failures: list[str] = []
    for service in ("postgres", "redis"):
        containers = run_command(
            [
                docker,
                "ps",
                "--all",
                "--quiet",
                "--filter",
                f"label=com.docker.compose.project={DATABASE_PROJECT}",
                "--filter",
                f"label=com.docker.compose.service={service}",
            ],
            capture_output=True,
        ).stdout.split()
        if len(containers) != 1:
            failures.append(f"{service}: expected one container, found {len(containers)}")
            continue

        state_result = run_command(
            [docker, "inspect", "--format", "{{json .State}}", containers[0]],
            capture_output=True,
        )
        state = json.loads(state_result.stdout)
        running = bool(state.get("Running"))
        health = str(state.get("Health", {}).get("Status", "none"))
        if not running or health != "healthy":
            failures.append(f"{service}: running={running}, health={health}")

    if failures:
        raise DeploymentError(
            "Database infrastructure is not ready: "
            + "; ".join(failures)
            + ". Start it with infra-database."
        )


def read_backend_version(uv: str) -> str:
    result = run_command(
        [uv, "version", "--project", str(BACKEND_ROOT), "--short"],
        capture_output=True,
    )
    version = result.stdout.strip()
    if not version:
        raise DeploymentError(f"Project version is missing in {BACKEND_ROOT / 'pyproject.toml'}")
    return version


def read_git_sha(git: str) -> str:
    result = run_command(
        [git, "rev-parse", "--short", "HEAD"],
        capture_output=True,
    )
    git_sha = result.stdout.strip()
    if not git_sha:
        raise DeploymentError("Git SHA is missing")
    return git_sha


def command_environment(environment: Environment) -> dict[str, str]:
    values = os.environ.copy()
    version = read_backend_version(find_tool("uv"))
    values["BACKEND_VERSION"] = version
    if environment is Environment.PROD:
        values["TAG"] = f"{version}-{read_git_sha(find_tool('git'))}"
    return values


@app.command()
def up(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to start: dev or prod."),
    ],
) -> None:
    """Build and start the application services."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    require_traefik_network(docker)
    require_database_stack(docker)

    if environment is Environment.DEV:
        message = "Starting the development environment"
        arguments = ("up", "--build", "--watch")
    else:
        message = f"Deploying web-app-backend:{values['TAG']}"
        arguments = ("up", "--detach", "--build")

    typer.secho(message, fg=typer.colors.CYAN, bold=True, err=True)
    run_command([*command, *arguments], process_environment=values)
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
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    run_command([*command, "ps"], process_environment=values)


@app.command()
def down(
    environment: Annotated[
        Environment,
        typer.Argument(help="Configuration to stop: dev or prod."),
    ],
) -> None:
    """Stop and remove the application services."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    typer.secho(
        f"Stopping the application ({environment.value})",
        fg=typer.colors.CYAN,
        bold=True,
        err=True,
    )
    run_command([*command, "down"], process_environment=values)
    typer.secho("Application is stopped.", fg=typer.colors.GREEN, bold=True, err=True)


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
