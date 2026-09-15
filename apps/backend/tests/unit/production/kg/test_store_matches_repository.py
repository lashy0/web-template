"""Contract test keeping the in-memory KG store honest.

A fake is only useful while it still matches the real repository. Without this
test the fake could keep answering a method the repository no longer has, and
every rule test would stay green against an API that does not exist - the exact
failure mode of an unspecced ``AsyncMock``.
"""

import inspect

import pytest

from app.domains.production.kg.repository import KgRepository
from tests.support.kg import InMemoryKgStore

# Helpers that shape test data or expose recorded state; they are not part of
# the repository surface and are deliberately excluded.
_TEST_ONLY_MEMBERS = frozenset(
    {
        "forget_operations",
        "happened_before",
        "operations",
        "prefixes",
        "units",
        "versions",
    }
)


def _emulated_methods() -> list[str]:
    return sorted(
        name
        for name, member in inspect.getmembers(InMemoryKgStore, inspect.isfunction)
        if not name.startswith(("_", "given_")) and name not in _TEST_ONLY_MEMBERS
    )


@pytest.mark.unit
def test_the_store_emulates_a_non_empty_slice_of_the_repository() -> None:
    assert _emulated_methods(), "the store must emulate at least one repository method"


@pytest.mark.unit
@pytest.mark.parametrize("method_name", _emulated_methods())
def test_every_emulated_method_exists_on_the_repository(method_name: str) -> None:
    assert hasattr(KgRepository, method_name), (
        f"InMemoryKgStore.{method_name} has no counterpart on KgRepository"
    )


@pytest.mark.unit
@pytest.mark.parametrize("method_name", _emulated_methods())
def test_every_emulated_method_accepts_the_repository_arguments(method_name: str) -> None:
    real = inspect.signature(getattr(KgRepository, method_name))
    fake = inspect.signature(getattr(InMemoryKgStore, method_name))

    assert [parameter.name for parameter in real.parameters.values()] == [
        parameter.name for parameter in fake.parameters.values()
    ], f"InMemoryKgStore.{method_name}{fake} does not match KgRepository.{method_name}{real}"
