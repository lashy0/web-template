"""Machine API wire shapes and the verification client's interface."""

from typing import Annotated, Literal, Protocol

import msgspec

SessionResult = Literal["passed", "failed", "aborted"]


class SessionResponse(msgspec.Struct, rename="camel", kw_only=True):
    """Only the server fields consumed by the simulator."""

    id: Annotated[str, msgspec.Meta(min_length=1)]
    firmware_version: str
    total_steps: Annotated[int, msgspec.Meta(ge=1)]
    completed_steps: Annotated[int, msgspec.Meta(ge=0)] = 0


class StepResponse(msgspec.Struct, rename="camel", kw_only=True):
    id: Annotated[str, msgspec.Meta(min_length=1)]
    step_no: Annotated[int, msgspec.Meta(ge=1)]


class SessionOpen(msgspec.Struct, rename="camel", kw_only=True):
    dev_eui: str
    slot_no: Annotated[int, msgspec.Meta(ge=1)]
    firmware_version: str
    total_steps: Annotated[int, msgspec.Meta(ge=1)]


class StepStart(msgspec.Struct, rename="camel", kw_only=True):
    step_no: Annotated[int, msgspec.Meta(ge=1)]
    check_name: str
    check_label: str
    defect_group_code: str


class StepComplete(msgspec.Struct, rename="camel", kw_only=True):
    status: Literal["passed", "failed"]
    measurement_value: float | None = None
    measurement_min: float | None = None
    measurement_max: float | None = None
    measurement_unit: str | None = None


class SessionComplete(msgspec.Struct, kw_only=True):
    status: SessionResult


class VerificationClient(Protocol):
    async def authenticate(self) -> None: ...

    async def aclose(self) -> None: ...

    async def open_session(
        self,
        *,
        dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> SessionResponse: ...

    async def start_step(
        self,
        session_id: str,
        *,
        step_no: int,
        name: str,
        label: str,
        group: str,
    ) -> StepResponse: ...

    async def complete_step(
        self,
        session_id: str,
        *,
        step_no: int,
        passed: bool,
        value: float | None,
        low: float | None,
        high: float | None,
        unit: str | None,
    ) -> StepResponse: ...

    async def complete_session(
        self,
        session_id: str,
        result: SessionResult,
    ) -> SessionResponse: ...


class ClientFactory(Protocol):
    def __call__(self,
        *,
        server: str,
        client_id: str,
        access_key: str,
        verify: bool,
    ) -> VerificationClient: ...
