import json
import os
import time
from typing import Annotated

import typer

from cli import database
from cli.compose import (
    DATABASE_NETWORK,
    IDENTITY_NETWORK,
    INFRASTRUCTURE_ROOT,
    TRAEFIK_NETWORK,
    ComposeProject,
    DeploymentError,
    Environment,
    EnvironmentArgument,
    HealthTimeoutOption,
    ServicesArgument,
    find_tool,
    follow_logs,
    image_exists,
    require_network,
    run_command,
)
from cli.otk import backend_command
from cli.output import ServiceStatus, announce, heading, print_status, report
from cli.release import DEV_VERSION, UNBUILT_VERSION, read_release_version

IMAGE = "otk-app-backend"
PROJECT = ComposeProject(
    "otk-app-backend",
    "Backend",
    "backend",
    INFRASTRUCTURE_ROOT / "backend",
    jobs=("prestart",),
)

backend_app = typer.Typer(
    help="Manage the backend.",
    no_args_is_help=True,
    add_completion=False,
)

WatchOption = Annotated[
    bool,
    typer.Option("--watch", help="Keep syncing backend source changes after startup (dev only)."),
]


def application_url(environment: Environment) -> str:
    scheme = "http" if environment is Environment.DEV else "https"

    return f"{scheme}://{PROJECT.setting('APP_HOST')}"


def addresses(environment: Environment) -> list[tuple[str, str]]:
    return [("API docs", f"{application_url(environment)}/api/schema")]


def require_database_stack(docker: str) -> None:
    require_network(docker, DATABASE_NETWORK, "Start the database first: infra database up.")

    failures: list[str] = []
    for service in ("postgres", "redis"):
        containers = run_command(
            [
                docker,
                "ps",
                "--all",
                "--quiet",
                "--filter",
                f"label=com.docker.compose.project={database.PROJECT.name}",
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
            + ". Start it with: infra database up."
        )


def command_environment(environment: Environment, *, build: bool = False) -> dict[str, str]:
    values = os.environ.copy()

    if environment is Environment.PROD:
        version = read_release_version() if build else UNBUILT_VERSION
        values["BACKEND_VERSION"] = version
        values["BACKEND_TAG"] = version
    else:
        values["BACKEND_VERSION"] = DEV_VERSION

    return values


def ensure_admin(docker: str) -> str:
    """Create the first administrator unless one exists; return what the backend reports."""
    result = run_command(
        backend_command(docker, ["users", "ensure-admin"]), check=False, capture_output=True
    )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DeploymentError(f"Could not create the first administrator. {detail}")

    return result.stdout.strip()


def start(environment: Environment, *, health_timeout: int = 120) -> str:
    """Build and start the services and create the first administrator if needed.

    A release image is built only once. Returns the credentials of a created
    administrator, or an empty string.
    """
    values = command_environment(environment, build=True)
    release = values.get("BACKEND_TAG")
    heading(PROJECT.title, release)
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment, process_environment=values)
    require_network(docker, TRAEFIK_NETWORK, "Start Traefik first: infra traefik up.")
    require_network(docker, IDENTITY_NETWORK, "Start identity first: infra identity up.")
    require_database_stack(docker)

    arguments = ["--detach", "--wait", "--wait-timeout", str(health_timeout)]

    if release is None or not image_exists(docker, f"{IMAGE}:{release}"):
        arguments.extend(("--build", "--quiet-build"))

    PROJECT.up(command, arguments, environment, process_environment=values)

    return ensure_admin(docker)


def stop(environment: Environment) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    run_command([*command, "down"], process_environment=values)


def status_section(environment: Environment) -> tuple[str, list[ServiceStatus]]:
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)

    return PROJECT.title, PROJECT.statuses(docker, command, process_environment=values)


def watch_changes(environment: Environment) -> None:
    """Sync backend source changes into the running dev containers until Ctrl+C."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    announce("\nWatching backend files. Press Ctrl+C to stop; the containers keep running.")
    run_command([*command, "watch", "--no-up"], process_environment=values)


@backend_app.command()
def up(
    environment: EnvironmentArgument,
    watch: WatchOption = False,
    health_timeout: HealthTimeoutOption = 120,
) -> None:
    """Build and start the backend services and wait until they are healthy.

    A release image is built once; deploying the same release again, for
    example on a rollback, reuses it.
    """
    if watch and environment is not Environment.DEV:
        raise DeploymentError("--watch is available only for the dev environment.")

    started = time.monotonic()
    admin = start(environment, health_timeout=health_timeout)
    report("Ready", started, addresses(environment), notes=[admin])

    if watch:
        watch_changes(environment)


@backend_app.command()
def down(environment: EnvironmentArgument) -> None:
    """Stop and remove the backend services."""
    started = time.monotonic()
    stop(environment)
    report("Stopped", started)


@backend_app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of the backend services."""
    print_status([status_section(environment)])


@backend_app.command()
def logs(environment: EnvironmentArgument, services: ServicesArgument = None) -> None:
    """Follow the logs of the API, the worker and the migrations."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    follow_logs(command, services, process_environment=values)
