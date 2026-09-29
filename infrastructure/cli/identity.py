import time

import typer

from cli.compose import (
    DATABASE_NETWORK,
    IDENTITY_NETWORK,
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
    require_network,
    run_command,
)
from cli.output import ServiceStatus, heading, print_status, report

IDENTITY_ROOT = INFRASTRUCTURE_ROOT / "identity"
PROJECT = ComposeProject(
    "otk-app-identity",
    "Identity",
    "identity",
    IDENTITY_ROOT,
    (ROOT_ENV_FILE, IDENTITY_ROOT / ".env"),
    jobs=("kratos-migrate", "hydra-migrate"),
)

identity_app = typer.Typer(
    help="Manage the Ory Kratos and Hydra identity infrastructure.",
    no_args_is_help=True,
    add_completion=False,
)


def addresses(environment: Environment) -> list[tuple[str, str]]:
    # Production publishes no identity ports; development only the Admin APIs.
    if environment is Environment.PROD:
        return []
    return [
        ("Kratos admin", f"http://127.0.0.1:{PROJECT.setting('KRATOS_ADMIN_PORT', '4434')}"),
        ("Hydra admin", f"http://127.0.0.1:{PROJECT.setting('HYDRA_ADMIN_PORT', '4445')}"),
    ]


def start(environment: Environment, *, health_timeout: int = 90) -> None:
    heading(PROJECT.title)
    docker = find_tool("docker")
    require_network(docker, DATABASE_NETWORK, "Start the database first: infra database up.")
    require_network(docker, TRAEFIK_NETWORK, "Start Traefik first: infra traefik up.")
    ensure_network(docker, IDENTITY_NETWORK)
    command = PROJECT.prepare(docker, environment)
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


@identity_app.command()
def up(environment: EnvironmentArgument, health_timeout: HealthTimeoutOption = 90) -> None:
    """Run migrations, start Kratos and Hydra, and wait until both are healthy."""
    started = time.monotonic()
    start(environment, health_timeout=health_timeout)
    report("Ready", started, addresses(environment))


@identity_app.command()
def down(environment: EnvironmentArgument) -> None:
    """Stop Kratos and Hydra while preserving their external network and databases."""
    started = time.monotonic()
    stop(environment)
    report("Stopped", started)


@identity_app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of Kratos and Hydra and of failed migrations."""
    print_status([status_section(environment)])


@identity_app.command()
def logs(environment: EnvironmentArgument, services: ServicesArgument = None) -> None:
    """Follow the logs of Kratos, Hydra and their migrations."""
    docker = find_tool("docker")
    follow_logs(PROJECT.prepare(docker, environment), services)
