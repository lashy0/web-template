"""Create the ignored environment files from their examples.

Values that are ``replace-with-...`` placeholders in an example are generated.
Existing files keep every value they have; only keys missing from them are
appended, so the command can be repeated after an example gains a key.
"""

import base64
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import bcrypt
from rich.text import Text

from cli.compose import (
    ENV_ASSIGNMENT,
    INFRASTRUCTURE_ROOT,
    REPOSITORY_ROOT,
    ROOT_ENV_FILE,
    parse_env,
    read_env_file,
)
from cli.output import columns, console

TRAEFIK_ENV_FILE = INFRASTRUCTURE_ROOT / "traefik" / ".env"
ENV_FILES = (
    ROOT_ENV_FILE,
    INFRASTRUCTURE_ROOT / "identity" / ".env",
    TRAEFIK_ENV_FILE,
)
PRODUCTION_KEYS = {
    ROOT_ENV_FILE: ("APP_HOST",),
    TRAEFIK_ENV_FILE: ("ACME_EMAIL", "TRAEFIK_DASHBOARD_ADDRESS"),
}
"""Keys a production deployment needs but only the operator can set."""
_DEVELOPMENT_VALUES = {"", "localhost", "127.0.0.1"}
PLACEHOLDER_PREFIX = "replace-with-"


@dataclass(slots=True)
class FillResult:
    created: bool = False
    added: list[str] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)


def _generate(key: str) -> tuple[str, str | None]:
    """Return a new value for ``key`` and a comment to write above it, if any."""
    match key:
        case "KRATOS_CIPHER_SECRET":
            # Kratos requires exactly 32 characters.
            return secrets.token_hex(16), None
        case "BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY":
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(), None
        case "TRAEFIK_USERNAME":
            return "admin", None
        case "TRAEFIK_HASHED_PASSWORD":
            password = secrets.token_urlsafe(18)
            # Traefik accepts the $2a$ and $2y$ bcrypt variants, not $2b$.
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(prefix=b"2a")).decode()
            # Single quotes keep Docker Compose from interpolating the $ signs.
            return f"'{hashed}'", f"Dashboard password: {password}"
        case _:
            # Hex values are safe in PostgreSQL DSNs and the Redis ACL file.
            return secrets.token_hex(32), None


def _display(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def fill_env_file(target: Path, example: Path) -> FillResult:
    """Create or complete ``target`` from ``example``."""
    existing = target.read_text(encoding="utf-8") if target.is_file() else None
    present = parse_env(existing) if existing is not None else {}
    result = FillResult(created=existing is None)
    lines: list[str] = []

    for line in example.read_text(encoding="utf-8").splitlines():
        match = ENV_ASSIGNMENT.match(line)
        if match is None or match["key"] in present:
            # Comments and layout are copied only into a new file.
            if existing is None:
                lines.append(line)

            continue

        key, value = match["key"], match["value"].strip()
        if value.startswith(PLACEHOLDER_PREFIX):
            value, comment = _generate(key)
            result.generated.append(key)

            if comment is not None:
                lines.append(f"# {comment}")

        lines.append(f"{key}={value}")
        result.added.append(key)

    if existing is None:
        target.touch(mode=0o600)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    elif result.added:
        separator = "" if not existing or existing.endswith("\n") else "\n"

        with target.open("a", encoding="utf-8", newline="\n") as file:
            file.write(separator + "\n".join(lines) + "\n")

    return result


def _describe(result: FillResult) -> Text:
    generated = f", {len(result.generated)} generated" if result.generated else ""

    if result.created:
        return Text.assemble(("created", "green"), generated)

    if result.added:
        return Text.assemble((f"added {', '.join(result.added)}", "yellow"), generated)

    return Text("up to date", style="dim")


def _unset_production_keys() -> dict[Path, list[str]]:
    unset: dict[Path, list[str]] = {}

    for path, keys in PRODUCTION_KEYS.items():
        values = read_env_file(path)

        if missing := [key for key in keys if values.get(key, "") in _DEVELOPMENT_VALUES]:
            unset[path] = missing

    return unset


def init() -> None:
    """Create the environment files from their examples and generate the secrets."""
    results = {
        target: fill_env_file(target, target.with_name(".env.example")) for target in ENV_FILES
    }

    console.print("Environment files", style="bold")
    console.print(
        columns(
            ((_display(target), _describe(result)) for target, result in results.items()), indent=2
        )
    )

    if "TRAEFIK_HASHED_PASSWORD" in results[TRAEFIK_ENV_FILE].generated:
        user = read_env_file(TRAEFIK_ENV_FILE).get("TRAEFIK_USERNAME")
        console.print(
            f"\nTraefik dashboard: user {user}, the password is in a comment in "
            f"{_display(TRAEFIK_ENV_FILE)}."
        )

    if unset := _unset_production_keys():
        console.print("\nSet before a production deployment:", style="bold")
        console.print(
            columns(((_display(path), ", ".join(keys)) for path, keys in unset.items()), indent=2)
        )

    console.print("\nNext: infra up dev")
