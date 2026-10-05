"""Scenario input models, normalization and validation."""

from functools import cached_property
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from pak_simulator.config.environment import ENV_REFERENCE
from pak_simulator.config.spans import TIME_PATTERN, VALUE_PATTERN, parse_time, parse_value
from pak_simulator.values import Span


def _number_input(value: object) -> object:
    if isinstance(value, bool):
        raise ValueError("Expected a number, not a boolean")

    return value


def _time_span(value: object) -> Span:
    if isinstance(value, Span):
        if value.low < 0:
            raise ValueError("Time must be nonnegative")

        return value

    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError("Expected a nonnegative time, e.g. 25s, 500ms or 1s..3s")

    return parse_time(value)


def _value_span(value: object) -> Span:
    if isinstance(value, Span):
        return value

    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError("Expected a number or numeric range, e.g. 205..225")

    return parse_value(value)


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Integer = Annotated[int, BeforeValidator(_number_input)]
Number = Annotated[FiniteFloat, BeforeValidator(_number_input)]
EnvironmentText = Annotated[str, Field(pattern=rf"^{ENV_REFERENCE.pattern}$")]
DevEui = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[0-9A-Fa-f]{16}$"),
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "string", "pattern": r"^\s*[0-9A-Fa-f]{16}\s*$"},
                {"type": "string", "pattern": rf"^{ENV_REFERENCE.pattern}$"},
            ]
        }
    ),
]
TimeInput = Annotated[
    FiniteFloat, Field(ge=0)
] | Annotated[str, Field(pattern=TIME_PATTERN)] | EnvironmentText
ValueInput = FiniteFloat | Annotated[str, Field(pattern=VALUE_PATTERN)] | EnvironmentText
TimeSpec = Annotated[
    Span,
    BeforeValidator(_time_span, json_schema_input_type=TimeInput),
    Field(description="A time: seconds as a number, `25s`, `1.5m`, `500ms` or a range `24s..27s`."),
]
ValueSpec = Annotated[
    Span,
    BeforeValidator(_value_span, json_schema_input_type=ValueInput),
    Field(description="A value: a number or range `205..225`, preserving the written decimal precision."),
]
Probability = Annotated[Number, Field(ge=0, le=1)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, hide_input_in_errors=True)


class DevEuiRange(_Model):
    """Consecutive DevEUIs of a batch."""

    from_: Annotated[
        DevEui,
        Field(description="The first DevEUI."),
    ] = Field(alias="from")
    count: Annotated[
        Integer,
        Field(ge=1, description="How many DevEUIs to take."),
        WithJsonSchema(
            {
                "anyOf": [
                    {"type": "integer", "minimum": 1},
                    {"type": "string", "pattern": rf"^{ENV_REFERENCE.pattern}$"},
                ]
            }
        ),
    ]

    @model_validator(mode="after")
    def check_overflow(self) -> Self:
        if int(self.from_, 16) + self.count - 1 > 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError("The DevEUI range goes past FFFFFFFFFFFFFFFF.")

        return self


class PakSpec(_Model):
    """A PAK with its slots and KG units."""

    code: Annotated[Title, Field(description="The PAK code, shown by the simulator.")]
    client_id: Annotated[
        str, Field(min_length=1, description="The PAK's OAuth client ID, usually `${PAK1_CLIENT_ID}`.")
    ]
    access_key: Annotated[
        str, Field(min_length=1, description="The PAK's access key, usually `${PAK1_ACCESS_KEY}`.")
    ]
    profile: Annotated[str, Field(min_length=1, description="A key of `profiles`.")]
    slots: Annotated[Integer, Field(ge=1, le=32)] = 6
    dev_eui: Annotated[
        DevEuiRange | Annotated[list[DevEui], Field(min_length=1)],
        Field(description="KG units to verify: a range `{from, count}` or a list of DevEUIs."),
    ]

    @field_validator("client_id", "access_key")
    @classmethod
    def nonblank_credentials(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PAK credentials must not be blank.")

        return value

    @cached_property
    def dev_euis(self) -> tuple[str, ...]:
        if isinstance(self.dev_eui, list):
            return tuple(dict.fromkeys(value.upper() for value in self.dev_eui))

        first = int(self.dev_eui.from_, 16)

        return tuple(f"{value:016X}" for value in range(first, first + self.dev_eui.count))


class CheckSpec(_Model):
    """A check as a healthy KG unit passes it."""

    name: Annotated[
        Title,
        Field(max_length=128, description="The check name in the PAK, such as `TestLoRa`."),
    ]
    label: Annotated[
        Title,
        Field(max_length=255, description="The check label shown to people."),
    ]
    group: Annotated[
        Title,
        Field(max_length=32, description="The defect group code from the defect dictionary."),
    ]
    time: TimeSpec
    value: ValueSpec | None = None
    unit: Annotated[str, Field(max_length=32)] | None = None
    limits: Annotated[
        tuple[Number | None, Number | None] | None,
        Field(description="`[min, max]`; a check without limits fails only through a defect."),
    ] = None
    critical: Annotated[bool, Field(description="A failure ends the session.")] = False

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("limits")
    @classmethod
    def check_limits(
        cls,
        value: tuple[float | None, float | None] | None
    ) -> tuple[float | None, float | None] | None:
        if value is None or value == (0, 0):
            return None  # PAKs report a check without limits as 0..0.

        low, high = value

        if low is not None and high is not None and low > high:
            raise ValueError("The minimum limit is above the maximum.")

        return value


class EffectSpec(_Model):
    """How a defect changes a check."""

    value: ValueSpec | None = None
    name: Annotated[
        Title,
        Field(max_length=128, description="Another check name the PAK reports instead."),
    ] | None = None
    label: Annotated[
        Title,
        Field(max_length=255, description="The check label shown to people."),
    ] | None = None
    time: TimeSpec | None = None
    status: Annotated[
        Literal["passed", "failed"] | None,
        Field(description="The result instead of the one computed from the limits."),
    ] = None


class DefectSpec(_Model):
    """A fault of a KG unit."""

    chance: Annotated[Probability, Field(description="The share of units with this fault.")]
    persists: Annotated[
        Probability,
        Field(description="The chance the fault is still there when the unit is retested."),
    ] = 1.0
    steps: Annotated[
        dict[str, ValueSpec | EffectSpec],
        Field(description="Checks by name or label: a new value, or the changes."),
    ]
    transient: Annotated[
        bool,
        Field(
            description=(
                "A condition of the test rather than of the unit, such as radio interference: "
                "rolled at its chance for every session, retests included; `persists` is ignored."
            )
        ),
    ] = False


class ProfileSpec(_Model):
    """The checks a PAK runs for a KG version, in order."""

    firmware_version: Annotated[
        Title,
        Field(max_length=64, description="The KG firmware version the PAK reports."),
    ]
    checks: Annotated[list[CheckSpec], Field(min_length=1)]
    defects: dict[str, DefectSpec] = Field(default_factory=dict)
    pass_rate: Annotated[
        Probability | None,
        Field(
            description=(
                "Probability of a passed session (0 to 1). When set, controls the outcome and "
                "generates matching check results; when omitted, defects and limits determine the outcome."
            )
        ),
    ] = None

    @model_validator(mode="after")
    def check_defect_targets(self) -> Self:
        targets = {check.name for check in self.checks} | {check.label for check in self.checks}

        for key, defect in self.defects.items():
            unknown = sorted(set(defect.steps) - targets)

            if unknown:
                raise ValueError(
                    f"Defect {key}: no checks {', '.join(map(repr, unknown))}. Name a check by its name or label."
                )

        return self


class RetestSpec(_Model):
    chance: Annotated[
        Probability,
        Field(description="The chance a failed unit is verified again."),
    ] = 0.5
    other_slot: Annotated[
        Probability,
        Field(description="The chance it is moved to another slot for that."),
    ] = 0.5
    max_attempts: Annotated[
        Integer,
        Field(ge=1, description="How many times a unit is verified at most."),
    ] = 3
    pause: Annotated[
        TimeSpec,
        Field(description="Pause before a retest in the same slot."),
    ] = Field(
        default_factory=lambda: Span(5, 15), json_schema_extra={"default": "5s..15s"}
    )


class SessionsSpec(_Model):
    """Session scheduling, interruptions and retries."""

    loading: Annotated[
        Literal["independent", "together"],
        Field(
            description=(
                "`independent`: each slot is reloaded as soon as it finishes. `together`: all slots are "
                "loaded at once, failed units are retested in their slot, and the next units go in only "
                "when every slot has finished."
            )
        ),
    ] = "independent"
    start: Annotated[
        TimeSpec,
        Field(description="Delay before a slot is loaded: the first time, or within each load when loading together."),
    ] = Field(default_factory=lambda: Span(0, 15), json_schema_extra={"default": "0s..15s"})
    swap: Annotated[
        TimeSpec,
        Field(description="Pause between units in a slot, or between loads when loading together."),
    ] = Field(default_factory=lambda: Span(8, 20), json_schema_extra={"default": "8s..20s"})
    abandon: Annotated[
        Probability,
        Field(description="Probability of a session being interrupted halfway."),
    ] = 0.0
    retest: RetestSpec = Field(default_factory=RetestSpec)


class ScenarioSpec(_Model):
    """A PAK simulator scenario."""

    server: Annotated[
        AnyHttpUrl,
        Field(description="The application address, such as `http://localhost`."),
        WithJsonSchema(
            {
                "anyOf": [
                    {"type": "string", "format": "uri"},
                    {"type": "string", "pattern": rf"^{ENV_REFERENCE.pattern}$"},
                ]
            }
        ),
    ]
    verify_tls: bool = True
    sessions: SessionsSpec = Field(default_factory=SessionsSpec)
    paks: Annotated[list[PakSpec], Field(min_length=1)]
    profiles: dict[str, ProfileSpec]

    @field_validator("server", mode="before")
    @classmethod
    def check_address_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()

            if any(char.isspace() for char in value):
                raise ValueError("Server address must not contain whitespace.")

            if "://" not in value or value.partition("://")[2].startswith("/"):
                raise ValueError("Server address must include a scheme and host, e.g. http://localhost.")

        return value

    @field_validator("server")
    @classmethod
    def check_address_parts(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.query is not None or value.fragment is not None:
            raise ValueError("Server address must not contain a query string or fragment.")

        return value

    @model_validator(mode="after")
    def check_paks(self) -> Self:
        codes = [pak.code for pak in self.paks]

        if len(set(codes)) != len(codes):
            raise ValueError("PAK codes in `paks` repeat.")

        client_owners: dict[str, str] = {}
        unit_owners: dict[str, str] = {}

        for pak in self.paks:
            if pak.profile not in self.profiles:
                raise ValueError(f"PAK {pak.code}: no profile {pak.profile!r} in `profiles`.")

            if pak.client_id in client_owners:
                raise ValueError(f"PAKs {client_owners[pak.client_id]} and {pak.code} use the same OAuth client ID.")

            client_owners[pak.client_id] = pak.code

            for dev_eui in pak.dev_euis:
                if dev_eui in unit_owners:
                    raise ValueError(f"PAKs {unit_owners[dev_eui]} and {pak.code} both select DevEUI {dev_eui}.")

                unit_owners[dev_eui] = pak.code

        return self


def schema() -> dict[str, Any]:
    """Export an editor schema for YAML before environment substitution."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **ScenarioSpec.model_json_schema()}
