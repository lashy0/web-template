import time

import typer

from cli.compose import (
    INFRASTRUCTURE_ROOT,
    ROOT_ENV_FILE,
    TRAEFIK_NETWORK,
    ComposeProject,
    Environment,
    EnvironmentArgument,
    HealthTimeoutOption,
    ServicesArgument,
    ensure_network,
    find_tool,
    follow_logs,
    run_command,
)
from cli.output import ServiceStatus, heading, print_status, report

TRAEFIK_ROOT = INFRASTRUCTURE_ROOT / "traefik"
PROJECT = ComposeProject(
    "otk-app-traefik", "Traefik", "traefik", TRAEFIK_ROOT, (ROOT_ENV_FILE, TRAEFIK_ROOT / ".env")
)

traefik_app = typer.Typer(
    help="Manage Traefik.",
    no_args_is_help=True,
    add_completion=False,
)


def addresses(environment: Environment) -> list[tuple[str, str]]:
    host = (
        "127.0.0.1"
        if environment is Environment.DEV
        else PROJECT.setting("TRAEFIK_DASHBOARD_ADDRESS")
    )

    return [("Traefik", f"http://{host}:8080/dashboard/")]


def start(environment: Environment, *, health_timeout: int = 60) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    ensure_network(docker, TRAEFIK_NETWORK)
    PROJECT.up(command, ["--detach", "--wait", "--wait-timeout", str(health_timeout)], environment)


def stop(environment: Environment) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)
    run_command([*command, "down"])


def status_section(environment: Environment) -> tuple[str, list[ServiceStatus]]:
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)

    return PROJECT.title, PROJECT.statuses(docker, command)


@traefik_app.command()
def up(environment: EnvironmentArgument, health_timeout: HealthTimeoutOption = 60) -> None:
    """Start or update Traefik and wait until it is healthy."""
    started = time.monotonic()
    start(environment, health_timeout=health_timeout)
    report("Ready", started, addresses(environment))


@traefik_app.command()
def down(environment: EnvironmentArgument) -> None:
    """Stop Traefik while keeping its external network and persistent data."""
    started = time.monotonic()
    stop(environment)
    report("Stopped", started)


@traefik_app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of Traefik."""
    print_status([status_section(environment)])


@traefik_app.command()
def logs(environment: EnvironmentArgument, services: ServicesArgument = None) -> None:
    """Follow the Traefik logs."""
    docker = find_tool("docker")
    follow_logs(PROJECT.prepare(docker, environment), services)
