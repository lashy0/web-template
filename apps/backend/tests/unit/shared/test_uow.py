from __future__ import annotations

import pytest

from app.shared.uow import PostCommitExecutor, transaction


class _Transaction:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> _Transaction:
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        self._events.append("rollback" if exc_type is not None else "commit")


class _Session:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def begin(self) -> _Transaction:
        return _Transaction(self._events)


class _SessionFactory:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def __call__(self) -> _Session:
        return _Session(self._events)


class _Executor(PostCommitExecutor):
    def __init__(self, effects: list[object]) -> None:
        self.effects = effects

    async def execute(self, effect: object) -> None:
        self.effects.append(effect)


@pytest.mark.unit
async def test_effect_runs_only_after_transaction_commit() -> None:
    events: list[str] = []
    delivered: list[object] = []

    async with transaction(_SessionFactory(events), executor=_Executor(delivered)) as uow:  # type: ignore[arg-type]
        uow.after_commit("started")
        assert events == []
        assert delivered == []

    assert events == ["commit"]
    assert delivered == ["started"]


@pytest.mark.unit
async def test_effect_is_not_run_when_transaction_rolls_back() -> None:
    events: list[str] = []
    delivered: list[object] = []

    with pytest.raises(RuntimeError, match="abort"):
        async with transaction(_SessionFactory(events), executor=_Executor(delivered)) as uow:  # type: ignore[arg-type]
            uow.after_commit("must-not-run")
            raise RuntimeError("abort")

    assert events == ["rollback"]
    assert delivered == []


@pytest.mark.unit
async def test_multiple_effects_run_after_one_commit() -> None:
    events: list[str] = []
    delivered: list[object] = []

    async with transaction(_SessionFactory(events), executor=_Executor(delivered)) as uow:  # type: ignore[arg-type]
        uow.after_commit("first")
        uow.after_commit("second")

    assert events == ["commit"]
    assert delivered == ["first", "second"]


@pytest.mark.unit
async def test_effect_delivery_failure_does_not_undo_commit_or_block_other_effects() -> None:
    events: list[str] = []
    delivered: list[object] = []

    class _FailingExecutor:
        async def execute(self, effect: object) -> None:
            if effect == "broken":
                raise RuntimeError("broker unavailable")
            delivered.append(effect)

    async with transaction(_SessionFactory(events), executor=_FailingExecutor()) as uow:  # type: ignore[arg-type]
        uow.after_commit("broken")
        uow.after_commit("still-delivered")

    assert events == ["commit"]
    assert delivered == ["still-delivered"]
