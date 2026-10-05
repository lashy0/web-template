"""Load scenario variables and lazily resolve their references."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from pak_simulator.config.errors import ScenarioError
from pak_simulator.errors import file_error_message

ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def read_environment(path: Path, environ: Mapping[str, str]) -> Mapping[str, str]:
    settings = _EnvironmentSettings(
        files=tuple(
            dict.fromkeys((Path.cwd() / ".env", path.parent / ".env"))
        ),
        values=dict(environ),
    )

    return _Environment(settings, environ)


class _Environment(Mapping[str, str]):
    """Resolve only referenced file values, keeping caller values literal."""

    def __init__(self, settings: _EnvironmentSettings, environ: Mapping[str, str]) -> None:
        self._values = settings.values
        self._sources = settings.sources
        self._resolved = dict(environ)

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __contains__(self, name: object) -> bool:
        return name in self._values

    def __getitem__(self, name: str) -> str:
        if name not in self._values:
            raise KeyError(name)

        return self._resolve(name)

    def _resolve(self, name: str, chain: tuple[str, ...] = ()) -> str:
        if name in self._resolved:
            return self._resolved[name]

        if name not in self._values:
            owner = chain[-1] if chain else "scenario"
            root = chain[0] if chain else owner
            reference_chain = " -> ".join((*chain, name))
            location = f" in {self._sources[owner]}" if owner in self._sources else ""
            resolving = f" while resolving '{root}'" if root != owner else ""

            raise ScenarioError(
                f"Environment variable '{name}' referenced by '{owner}'{resolving} "
                f"(reference chain: {reference_chain}){location} is not set."
            )

        if name in chain:
            cycle_start = chain.index(name)
            cycle = " -> ".join((*chain[cycle_start:], name))

            raise ScenarioError(f"Circular environment reference: {cycle}.")

        self._resolved[name] = ENV_REFERENCE.sub(
            lambda match: self._resolve(match[1], (*chain, name)), self._values[name]
        )

        return self._resolved[name]


def expand_text(value: str, environ: Mapping[str, str]) -> str:
    """Expand one scalar, preserving quotes and newlines in secrets."""
    missing = sorted({name for name in ENV_REFERENCE.findall(value) if name not in environ})

    if missing:
        raise ScenarioError(
            f"Environment variables are not set: {', '.join(missing)}."
            " Set them in .env next to the scenario."
        )

    return ENV_REFERENCE.sub(lambda match: environ[match[1]], value)


class _EnvironmentSettings(BaseSettings):
    """One scenario's variables and their origin, without a process-wide cache."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=None,
        env_file_encoding="utf-8",
        enable_decoding=False,
        frozen=True,
        hide_input_in_errors=True,
    )

    files: tuple[Path, ...] = Field(exclude=True)
    values: dict[str, str] = Field(default_factory=dict, repr=False)
    sources: dict[str, Path] = Field(default_factory=dict, exclude=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # The supplied mapping is authoritative, including an explicitly empty one.
        # BaseSettings merges it over the file source without consulting os.environ.
        return init_settings, _ScenarioDotEnvSource(settings_cls)


class _ScenarioDotEnvSource(DotEnvSettingsSource):
    """Keep references literal until the selected PAK actually needs them."""

    def __call__(self) -> dict[str, Any]:
        self.sources: dict[str, Path] = {}
        self.env_file = self.current_state["files"]
        # Let the standard source handle multiple files and their precedence.
        values = self._read_env_files()

        return {"values": values, "sources": self.sources}

    def _read_env_file(self, file_path: Path) -> Mapping[str, str | None]:
        try:
            values = {
                key: value
                for key, value in dotenv_values(file_path, encoding=self.env_file_encoding, interpolate=False).items()
                if value is not None
            }
        except UnicodeDecodeError as exc:
            raise ScenarioError(
                f"Cannot read {file_path}: save the environment file using UTF-8 encoding."
            ) from exc
        except OSError as exc:
            raise ScenarioError(file_error_message(exc, file_path, action="read")) from exc

        self.sources.update(dict.fromkeys(values, file_path))

        return values
