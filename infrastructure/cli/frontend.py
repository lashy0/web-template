import os
import time

import typer

from cli.backend import application_url
from cli.compose import (
    INFRASTRUCTURE_ROOT,
    TRAEFIK_NETWORK,
    ComposeProject,
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
from cli.output import ServiceStatus, heading, print_status, report
from cli.release import UNBUILT_VERSION, read_release_version

IMAGE = "otk-app-frontend"
PROJECT = ComposeProject(
    "otk-app-frontend", "Frontend", "frontend", INFRASTRUCTURE_ROOT / "frontend"
)

frontend_app = typer.Typer(
    help="Manage the frontend.",
    no_args_is_help=True,
    add_completion=False,
)


def addresses(environment: Environment) -> list[tuple[str, str]]:
    return [("App", application_url(environment))]


def command_environment(environment: Environment, *, build: bool = False) -> dict[str, str]:
    values = os.environ.copy()

    if environment is Environment.PROD:
        values["FRONTEND_TAG"] = read_release_version() if build else UNBUILT_VERSION

    return values


def start(environment: Environment, *, health_timeout: int = 120) -> None:
    """Build and start the frontend; a release image is built only once."""
    values = command_environment(environment, build=True)
    release = values.get("FRONTEND_TAG")
    heading(PROJECT.title, release)
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment, process_environment=values)
    require_network(docker, TRAEFIK_NETWORK, "Start Traefik first: infra traefik up.")

    arguments = ["--detach", "--wait", "--wait-timeout", str(health_timeout)]

    if release is None or not image_exists(docker, f"{IMAGE}:{release}"):
        arguments.extend(("--build", "--quiet-build"))

    PROJECT.up(command, arguments, environment, process_environment=values)


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


@frontend_app.command()
def up(environment: EnvironmentArgument, health_timeout: HealthTimeoutOption = 120) -> None:
    """Build and start the frontend and wait until it is healthy.

    A release image is built once; deploying the same release again, for
    example on a rollback, reuses it.
    """
    started = time.monotonic()
    start(environment, health_timeout=health_timeout)
    report("Ready", started, addresses(environment))


@frontend_app.command()
def down(environment: EnvironmentArgument) -> None:
    """Stop and remove the frontend."""
    started = time.monotonic()
    stop(environment)
    report("Stopped", started)


@frontend_app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of the frontend."""
    print_status([status_section(environment)])


@frontend_app.command()
def logs(environment: EnvironmentArgument, services: ServicesArgument = None) -> None:
    """Follow the frontend logs, such as the Vite dev server output."""
    docker = find_tool("docker")
    values = command_environment(environment)
    command = PROJECT.prepare(docker, environment, process_environment=values)
    follow_logs(command, services, process_environment=values)
