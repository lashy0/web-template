"""Load and compile a YAML scenario into the simulation model."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from pak_simulator import model
from pak_simulator.config.environment import read_environment
from pak_simulator.config.errors import ScenarioError, validation_message
from pak_simulator.config.spec import CheckSpec, EffectSpec, ProfileSpec, ScenarioSpec
from pak_simulator.config.yaml_loader import decode_yaml, select_paks, substitute
from pak_simulator.errors import file_error_message
from pak_simulator.values import Span


def load(
    path: Path,
    *,
    server: str | None = None,
    pak_codes: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> model.Simulation:
    """Read YAML, resolve environment values and validate the resulting scenario."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ScenarioError(
            f"Cannot read {path}: save the scenario using UTF-8 encoding.",
        ) from exc
    except OSError as exc:
        raise ScenarioError(file_error_message(exc, path, action="read")) from exc

    environment = read_environment(path, os.environ if environ is None else environ)

    try:
        raw = decode_yaml(text)

        if isinstance(raw, dict):
            if server is not None:
                raw["server"] = server

            if pak_codes:
                select_paks(raw, pak_codes, environment)

        raw = substitute(raw, environment)
        spec = ScenarioSpec.model_validate(raw)

        return _compile_scenario(spec)
    except ValidationError as exc:
        raise ScenarioError(f"{path}:\n{validation_message(exc)}") from exc
    except ScenarioError as exc:
        raise ScenarioError(f"{path}: {exc}") from exc


def _compile_scenario(spec: ScenarioSpec) -> model.Simulation:
    profiles = {key: _compile_profile(key, item) for key, item in spec.profiles.items()}
    sessions = spec.sessions

    return model.Simulation(
        server=str(spec.server).rstrip("/"),
        verify_tls=spec.verify_tls,
        sessions=model.Sessions(
            start=sessions.start,
            swap=sessions.swap,
            abandon=sessions.abandon,
            retest=model.Retest(
                chance=sessions.retest.chance,
                other_slot=sessions.retest.other_slot,
                max_attempts=sessions.retest.max_attempts,
                pause=sessions.retest.pause,
            ),
            together=sessions.loading == "together",
        ),
        paks=tuple(
            model.Pak(
                code=pak.code,
                client_id=pak.client_id,
                access_key=pak.access_key,
                slots=pak.slots,
                profile=profiles[pak.profile],
                dev_euis=pak.dev_euis,
            )
            for pak in spec.paks
        ),
        profiles=tuple(profiles.values()),
    )


def _compile_profile(key: str, spec: ProfileSpec) -> model.Profile:
    return model.Profile(
        key=key,
        firmware_version=spec.firmware_version,
        checks=tuple(_compile_check(check) for check in spec.checks),
        defects=tuple(
            model.Defect(
                key=defect_key,
                chance=defect.chance,
                persists=defect.persists,
                effects={target: _compile_effect(effect) for target, effect in defect.steps.items()},
                transient=defect.transient,
            )
            for defect_key, defect in spec.defects.items()
        ),
        pass_rate=spec.pass_rate,
    )


def _compile_check(spec: CheckSpec) -> model.Check:
    low, high = spec.limits or (None, None)

    return model.Check(
        name=spec.name,
        label=spec.label,
        group=spec.group,
        time=spec.time,
        value=spec.value,
        unit=spec.unit,
        low=low,
        high=high,
        critical=spec.critical,
    )


def _compile_effect(spec: Span | EffectSpec) -> model.Effect:
    if isinstance(spec, Span):
        return model.Effect(value=spec)

    return model.Effect(
        value=spec.value,
        name=spec.name,
        label=spec.label,
        time=spec.time,
        passed=None if spec.status is None else spec.status == "passed",
    )
