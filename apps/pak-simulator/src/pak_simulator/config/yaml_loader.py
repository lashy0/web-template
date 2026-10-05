"""Parse and prepare scenario YAML before Pydantic validation."""

from collections.abc import Mapping, Sequence
from typing import Any

import yaml
from yaml.nodes import MappingNode

from pak_simulator.config.environment import expand_text
from pak_simulator.config.errors import ScenarioError


class _ScenarioLoader(yaml.SafeLoader):
    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._checked_mappings: set[int] = set()

    def flatten_mapping(self, node: MappingNode) -> None:
        if id(node) in self._checked_mappings:
            return

        self._checked_mappings.add(id(node))
        seen: dict[Any, int] = {}

        for key_node, _ in node.value:
            key = (
                key_node.value
                if key_node.tag in {"tag:yaml.org,2002:merge", "tag:yaml.org,2002:value"}
                else self.construct_object(key_node)
            )
            try:
                previous_line = seen.get(key)
                seen[key] = key_node.start_mark.line + 1
            except TypeError:
                # Let SafeLoader report an invalid non-scalar mapping key.
                return super().flatten_mapping(node)

            if previous_line is not None:
                raise ScenarioError(
                    f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}, "
                    f"column {key_node.start_mark.column + 1}; first defined at line {previous_line}."
                )
        # Check before flattening: local overrides of YAML merges are valid.
        super().flatten_mapping(node)


def decode_yaml(text: str) -> Any:
    try:
        return yaml.load(text, Loader=_ScenarioLoader)
    except yaml.YAMLError as exc:
        raise ScenarioError(str(exc)) from exc


def substitute(value: Any, environ: Mapping[str, str]) -> Any:
    """Return an expanded copy; shared aliases are valid, recursive aliases are not."""
    return _substitute(value, environ, {}, "$")


def _substitute(value: Any, environ: Mapping[str, str], active: dict[int, str], path: str) -> Any:
    if isinstance(value, str):
        return expand_text(value, environ)

    if not isinstance(value, list | dict):
        return value

    identity = id(value)

    if identity in active:
        raise ScenarioError(f"Circular YAML reference at {path}: refers back to {active[identity]}.")

    active[identity] = path

    try:
        if isinstance(value, list):
            return [
                _substitute(child, environ, active, f"{path}[{index}]")
                for index, child in enumerate(value)
            ]

        expanded: dict[Any, Any] = {}
        original_keys: dict[Any, Any] = {}

        for key, child in value.items():
            resolved_key = _substitute(key, environ, active, f"{path}.<key>")

            if resolved_key in expanded:
                raise ScenarioError(
                    f"Duplicate mapping key after environment expansion at {path}: "
                    f"{original_keys[resolved_key]!r} and {key!r} resolve to {resolved_key!r}."
                )

            original_keys[resolved_key] = key
            expanded[resolved_key] = _substitute(child, environ, active, f"{path}[{key!r}]")

        return expanded
    finally:
        del active[identity]


def select_paks(raw: dict[str, Any], pak_codes: Sequence[str], environment: Mapping[str, str]) -> None:
    """Keep selected entries and their profiles before resolving their settings."""
    paks = raw.get("paks")

    if not isinstance(paks, list):
        return  # Let ScenarioSpec report malformed input.

    selected = set(pak_codes)
    codes: set[str] = set()
    retained: list[Any] = []

    for pak in paks:
        if not isinstance(pak, dict) or not isinstance(pak.get("code"), str):
            retained.append(pak)  # A missing or invalid code cannot be used for selection.
            continue

        code = substitute(pak["code"], environment).strip()
        codes.add(code)

        if code in selected:
            retained.append(pak)

    unknown = sorted(selected - codes)

    if unknown:
        raise ScenarioError(f"No such PAK in the scenario: {', '.join(unknown)}")

    raw["paks"] = retained
    profiles = raw.get("profiles")

    if isinstance(profiles, dict):
        profile_keys = {
            substitute(pak["profile"], environment)
            for pak in retained
            if isinstance(pak, dict) and isinstance(pak.get("profile"), str)
        }
        retained_profiles = {}

        for key, profile in profiles.items():
            try:
                resolved_key = substitute(key, environment)
            except ScenarioError:
                # Unresolved keys cannot identify the already resolved selected profiles.
                continue

            if resolved_key in profile_keys:
                retained_profiles[key] = profile

        raw["profiles"] = retained_profiles
