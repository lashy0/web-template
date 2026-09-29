import time
from typing import Annotated

import typer

from cli.compose import (
    DATABASE_NETWORK,
    INFRASTRUCTURE_ROOT,
    ComposeProject,
    DeploymentError,
    Environment,
    EnvironmentArgument,
    ServicesArgument,
    ensure_network,
    find_tool,
    follow_logs,
    run_command,
)
from cli.output import ServiceStatus, heading, print_status, report

PROJECT = ComposeProject(
    "otk-app-database", "Database", "database", INFRASTRUCTURE_ROOT / "database"
)

database_app = typer.Typer(
    help="Manage PostgreSQL and Redis.",
    no_args_is_help=True,
    add_completion=False,
)


def addresses(environment: Environment) -> list[tuple[str, str]]:
    # Production publishes no database ports.
    if environment is Environment.PROD:
        return []

    return [
        ("PostgreSQL", f"127.0.0.1:{PROJECT.setting('POSTGRES_PORT', '5432')}"),
        ("Redis", f"127.0.0.1:{PROJECT.setting('REDIS_PORT', '6379')}"),
    ]


def require_no_clients(docker: str) -> None:
    """Refuse while containers of other projects are connected to the databases."""
    projects = run_command(
        [
            docker,
            "ps",
            "--filter",
            f"network={DATABASE_NETWORK}",
            "--format",
            '{{.Label "com.docker.compose.project"}}',
        ],
        capture_output=True,
    ).stdout.split()
    clients = sorted(set(projects) - {PROJECT.name})

    if clients:
        raise DeploymentError(
            f"The databases are still used by: {', '.join(clients)}. "
            "Stop these projects first, or pass --force."
        )


def start(environment: Environment) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    ensure_network(docker, DATABASE_NETWORK)
    command = PROJECT.prepare(docker, environment)
    PROJECT.up(command, ["--detach", "--wait", "postgres", "redis"], environment)


def stop(environment: Environment, *, force: bool = False) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)

    if not force:
        require_no_clients(docker)

    run_command([*command, "down"])


def status_section(environment: Environment) -> tuple[str, list[ServiceStatus]]:
    docker = find_tool("docker")
    command = PROJECT.prepare(docker, environment)

    return PROJECT.title, PROJECT.statuses(docker, command)


@database_app.command()
def up(environment: EnvironmentArgument) -> None:
    """Start the PostgreSQL and Redis data services."""
    started = time.monotonic()
    start(environment)
    report("Ready", started, addresses(environment))


@database_app.command()
def down(
    environment: EnvironmentArgument,
    force: Annotated[
        bool,
        typer.Option("--force", help="Stop even while other projects use the databases."),
    ] = False,
) -> None:
    """Stop the database containers while preserving their volumes."""
    started = time.monotonic()
    stop(environment, force=force)
    report("Stopped", started)


@database_app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of the database services."""
    print_status([status_section(environment)])


@database_app.command()
def logs(environment: EnvironmentArgument, services: ServicesArgument = None) -> None:
    """Follow the logs of PostgreSQL and Redis."""
    docker = find_tool("docker")
    follow_logs(PROJECT.prepare(docker, environment), services)
