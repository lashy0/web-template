"""Release versions: CalVer ``YEAR.MONTH.N`` taken from ``vYEAR.MONTH.N`` git tags.

N counts the releases of the month from 1. Parts have no leading zeros, which
both Python and npm versions reject or rewrite.
"""

import re
from datetime import date
from typing import Annotated

import typer

from cli.compose import DeploymentError, find_tool, run_command
from cli.output import console

TAG_PREFIX = "v"
DEV_VERSION = "dev"
UNBUILT_VERSION = "unbuilt"
"""The image tag for commands that build nothing, such as status and down."""
_VERSION_PATTERN = re.compile(r"(?P<year>[1-9]\d{3})\.(?P<month>[1-9]\d?)\.(?P<number>[1-9]\d*)")


def parse_version(version: str) -> tuple[int, int, int] | None:
    match = _VERSION_PATTERN.fullmatch(version)

    if match is None or int(match["month"]) > 12:
        return None

    return int(match["year"]), int(match["month"]), int(match["number"])


def next_version(existing: list[str], today: date) -> str:
    """Return the next release of the month of ``today`` after the ``existing`` versions."""
    numbers = [
        parsed[2]
        for parsed in map(parse_version, existing)
        if parsed is not None and parsed[:2] == (today.year, today.month)
    ]

    return f"{today.year}.{today.month}.{max(numbers, default=0) + 1}"


def _release_tags(git: str) -> list[str]:
    result = run_command([git, "tag", "--list", f"{TAG_PREFIX}*"], capture_output=True)

    return [tag.removeprefix(TAG_PREFIX) for tag in result.stdout.split()]


def _require_clean_worktree(git: str) -> None:
    result = run_command([git, "status", "--porcelain"], capture_output=True)
    if result.stdout.strip():
        raise DeploymentError(
            "The working tree has uncommitted changes. Commit or stash them first."
        )


def _head_release(git: str) -> str | None:
    result = run_command(
        [git, "tag", "--points-at", "HEAD", "--list", f"{TAG_PREFIX}*"],
        capture_output=True,
    )
    releases = [
        (parsed, version)
        for tag in result.stdout.split()
        if (parsed := parse_version(version := tag.removeprefix(TAG_PREFIX))) is not None
    ]

    return max(releases)[1] if releases else None


def read_release_version() -> str:
    """Return the release a production deployment builds: the tag of a clean HEAD."""
    git = find_tool("git")
    _require_clean_worktree(git)
    version = _head_release(git)

    if version is None:
        raise DeploymentError(
            "HEAD has no release tag. Check out a release, or create one with 'infra release'."
        )

    return version


def release(
    push: Annotated[
        bool,
        typer.Option("--push", help="Push the new tag to origin."),
    ] = False,
) -> None:
    """Tag HEAD as the next CalVer release, such as v2026.9.2."""
    git = find_tool("git")
    _require_clean_worktree(git)
    current = _head_release(git)

    if current is not None:
        raise DeploymentError(f"HEAD is already release {current}.")

    version = next_version(_release_tags(git), date.today())
    tag = f"{TAG_PREFIX}{version}"
    run_command([git, "tag", "--annotate", tag, "--message", f"Release {version}"])
    console.print(f"Tagged release {version} as {tag}.", style="bold green")

    if push:
        run_command([git, "push", "origin", tag])
    else:
        console.print(f"Publish it with: git push origin {tag}")
