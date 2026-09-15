"""Rules governing contiguous DevEUI allocation for a batch."""

import pytest

from app.domains.production.kg.commands import AllocateForBatch
from app.domains.production.kg.exceptions import (
    KgDevEuiPrefixArchivedError,
    KgDevEuiPrefixNotFoundError,
    KgDevEuiRangeOverflowError,
)
from app.domains.production.kg.queries import KgQueries
from tests.support.kg import InMemoryKgStore


@pytest.fixture
def store() -> InMemoryKgStore:
    return InMemoryKgStore()


@pytest.mark.unit
async def test_the_first_allocation_of_a_prefix_starts_at_one(store: InMemoryKgStore) -> None:
    """Suffix zero is never issued, so a fresh prefix begins at ...000001."""
    store.given_prefix("a1b2c3d4e5")

    allocation = await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=3)

    assert allocation.dev_euis == [
        "a1b2c3d4e5000001",
        "a1b2c3d4e5000002",
        "a1b2c3d4e5000003",
    ]


@pytest.mark.unit
async def test_allocation_continues_after_the_deveuis_already_taken(
    store: InMemoryKgStore,
) -> None:
    store.given_prefix("a1b2c3d4e5")
    store.given_allocated_units("a1b2c3d4e5", count=8)

    allocation = await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=3)

    assert allocation.dev_euis == [
        "a1b2c3d4e5000009",
        "a1b2c3d4e500000a",
        "a1b2c3d4e500000b",
    ]


@pytest.mark.unit
async def test_the_allocation_is_contiguous(store: InMemoryKgStore) -> None:
    store.given_prefix("a1b2c3d4e5")

    allocation = await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=25)

    suffixes = [int(dev_eui[-6:], 16) for dev_eui in allocation.dev_euis]
    assert len(allocation.dev_euis) == 25
    assert suffixes == list(range(suffixes[0], suffixes[0] + 25))


@pytest.mark.unit
async def test_the_preview_promises_exactly_what_allocation_delivers(
    store: InMemoryKgStore,
) -> None:
    """The batch creation form shows this range before committing to it."""
    store.given_prefix("a1b2c3d4e5")
    store.given_allocated_units("a1b2c3d4e5", count=8)

    first, last = await KgQueries(store).preview_allocation("a1b2c3d4e5", 3)
    allocation = await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=3)

    assert (first, last) == (allocation.dev_euis[0], allocation.dev_euis[-1])


@pytest.mark.unit
async def test_allocation_locks_the_prefix_but_a_preview_does_not(
    store: InMemoryKgStore,
) -> None:
    """Two concurrent batches must not be handed the same DevEUI range."""
    store.given_prefix("a1b2c3d4e5")

    await KgQueries(store).preview_allocation("a1b2c3d4e5", 1)
    assert "lock_allocation:a1b2c3d4e5" not in store.operations

    store.forget_operations()
    await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=1)
    assert store.happened_before("lock_allocation", "get_max_dev_eui_for_prefix")


@pytest.mark.unit
async def test_an_archived_prefix_can_neither_be_previewed_nor_allocated(
    store: InMemoryKgStore,
) -> None:
    store.given_prefix("a1b2c3d4e5", archived=True)

    with pytest.raises(KgDevEuiPrefixArchivedError):
        await KgQueries(store).preview_allocation("a1b2c3d4e5", 1)

    with pytest.raises(KgDevEuiPrefixArchivedError):
        await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=1)


@pytest.mark.unit
async def test_an_unknown_prefix_can_neither_be_previewed_nor_allocated(
    store: InMemoryKgStore,
) -> None:
    with pytest.raises(KgDevEuiPrefixNotFoundError):
        await KgQueries(store).preview_allocation("a1b2c3d4e5", 1)

    with pytest.raises(KgDevEuiPrefixNotFoundError):
        await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=1)


@pytest.mark.unit
async def test_allocation_is_refused_when_the_prefix_range_is_exhausted(
    store: InMemoryKgStore,
) -> None:
    store.given_prefix("a1b2c3d4e5")
    store.given_unit("a1b2c3d4e5ffffff")

    with pytest.raises(KgDevEuiRangeOverflowError):
        await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=1)


@pytest.mark.unit
async def test_allocation_is_refused_when_the_request_does_not_fit_the_remaining_range(
    store: InMemoryKgStore,
) -> None:
    store.given_prefix("a1b2c3d4e5")
    store.given_unit("a1b2c3d4e5fffffd")

    with pytest.raises(KgDevEuiRangeOverflowError):
        await AllocateForBatch(store).execute(prefix="a1b2c3d4e5", quantity=5)
