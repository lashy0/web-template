"""In-memory KG store with real behaviour, replacing repository mocks.

Why a fake and not ``AsyncMock``: an unspecced mock answers every attribute, so
a command calling a method the repository does not have still passes. This
store implements the exact ``KgRepository`` surface the KG commands and queries
use, keeps real state, and records an operation log so tests can assert on
*ordering* that matters (locking before a usage check) rather than on call
shape.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domains.production.kg.model import KgDevEuiPrefix, KgState, KgUnit, KgVersion

_SUFFIX_WIDTH = 6


class InMemoryKgStore:
    def __init__(self) -> None:
        self.prefixes: dict[str, KgDevEuiPrefix] = {}
        self.versions: dict[UUID, KgVersion] = {}
        self.units: dict[str, KgUnit] = {}
        self.operations: list[str] = []
        self._batches_per_prefix: dict[str, int] = {}
        self._batches_per_version: dict[UUID, int] = {}

    # ----------------------------------------------------------------- given

    def given_prefix(
        self,
        prefix: str = "a1b2c3d4e5",
        *,
        short_code: str = "kg",
        name: str = "Primary",
        archived: bool = False,
    ) -> KgDevEuiPrefix:
        item = KgDevEuiPrefix(
            prefix=prefix,
            short_code=short_code,
            name=name,
            created_at=datetime.now(UTC),
            archived_at=datetime.now(UTC) if archived else None,
        )
        self.prefixes[prefix] = item
        return item

    def given_version(
        self,
        code: str = "KG-1",
        *,
        name: str = "Version 1",
        description: str | None = None,
        archived: bool = False,
    ) -> KgVersion:
        now = datetime.now(UTC)
        item = KgVersion(
            id=uuid4(),
            code=code,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            archived_at=now if archived else None,
        )
        self.versions[item.id] = item
        return item

    def given_unit(
        self,
        dev_eui: str,
        *,
        batch_id: UUID | None = None,
        state: KgState = KgState.REGISTERED,
    ) -> KgUnit:
        now = datetime.now(UTC)
        unit = KgUnit(
            dev_eui=dev_eui,
            short_id=f"kg-{len(self.units) + 1:06d}",
            batch_id=batch_id or uuid4(),
            state=state,
            created_at=now,
            updated_at=now,
        )
        self.units[dev_eui] = unit
        return unit

    def given_allocated_units(
        self, prefix: str, *, count: int, starting_at: int = 1
    ) -> list[KgUnit]:
        """Occupy ``count`` consecutive DevEUIs so allocation must continue after them.

        Suffixes start at 1 because ``derive_dev_eui_range`` never issues 0.
        """
        return [
            self.given_unit(f"{prefix}{suffix:0{_SUFFIX_WIDTH}x}")
            for suffix in range(starting_at, starting_at + count)
        ]

    def given_batches_using_prefix(self, prefix: str, *, count: int) -> None:
        self._batches_per_prefix[prefix] = count

    def given_batches_using_version(self, version_id: UUID, *, count: int) -> None:
        self._batches_per_version[version_id] = count

    # ------------------------------------------------------------ inspection

    def forget_operations(self) -> None:
        """Drop the operation log so a later phase can be inspected on its own."""
        self.operations.clear()

    def happened_before(self, earlier: str, later: str) -> bool:
        """Whether ``earlier`` was recorded before ``later`` in the operation log."""
        recorded = [entry.split(":", 1)[0] for entry in self.operations]
        if earlier not in recorded or later not in recorded:
            raise AssertionError(f"expected both {earlier} and {later} in {recorded}")
        return recorded.index(earlier) < recorded.index(later)

    # ---------------------------------------------------------------- prefix

    async def get_prefix(self, prefix: str, *, for_update: bool = False) -> KgDevEuiPrefix | None:
        self.operations.append(f"get_prefix:{prefix}")
        return self.prefixes.get(prefix)

    async def get_prefix_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        self.operations.append(f"get_prefix_by_short_code:{short_code}")
        return next(
            (item for item in self.prefixes.values() if item.short_code == short_code),
            None,
        )

    async def save_prefix(self, item: KgDevEuiPrefix) -> KgDevEuiPrefix:
        self.operations.append(f"save_prefix:{item.prefix}")
        self.prefixes[item.prefix] = item
        return item

    async def delete_prefix(self, item: KgDevEuiPrefix) -> None:
        self.operations.append(f"delete_prefix:{item.prefix}")
        del self.prefixes[item.prefix]

    async def count_batches_for_prefix(self, prefix: str) -> int:
        self.operations.append(f"count_batches_for_prefix:{prefix}")
        return self._batches_per_prefix.get(prefix, 0)

    async def lock_allocation(self, prefix: str) -> None:
        self.operations.append(f"lock_allocation:{prefix}")

    async def get_max_dev_eui_for_prefix(self, prefix: str) -> str | None:
        self.operations.append(f"get_max_dev_eui_for_prefix:{prefix}")
        occupied = sorted(dev_eui for dev_eui in self.units if dev_eui.startswith(prefix))
        return occupied[-1] if occupied else None

    # --------------------------------------------------------------- version

    async def get_version(self, version_id: UUID, *, for_update: bool = False) -> KgVersion | None:
        self.operations.append(f"get_version:{version_id}")
        return self.versions.get(version_id)

    async def get_version_by_code(self, code: str) -> KgVersion | None:
        self.operations.append(f"get_version_by_code:{code}")
        return next((item for item in self.versions.values() if item.code == code), None)

    async def save_version(self, item: KgVersion) -> KgVersion:
        self.operations.append(f"save_version:{item.code}")
        self.versions[item.id] = item
        return item

    async def delete_version(self, item: KgVersion) -> None:
        self.operations.append(f"delete_version:{item.code}")
        del self.versions[item.id]

    async def count_batches_for_version(self, version_id: UUID) -> int:
        self.operations.append(f"count_batches_for_version:{version_id}")
        return self._batches_per_version.get(version_id, 0)

    # ------------------------------------------------------------------ unit

    async def get_by_dev_eui(self, dev_eui: str, *, for_update: bool = False) -> KgUnit | None:
        self.operations.append(f"get_by_dev_eui:{dev_eui}")
        return self.units.get(dev_eui)

    async def update_state(self, kg: KgUnit, *, state: KgState) -> KgUnit:
        self.operations.append(f"update_state:{kg.dev_eui}")
        kg.state = state
        return kg

    async def delete_unit(self, kg: KgUnit) -> None:
        self.operations.append(f"delete_unit:{kg.dev_eui}")
        del self.units[kg.dev_eui]


class StubVerificationHistory:
    """Verification facts production deletion rules consult, as plain state."""

    def __init__(self, *, dev_euis_with_history: set[str] | None = None) -> None:
        self._dev_euis = dev_euis_with_history or set()

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
        return False

    async def has_history_for_kg(self, dev_eui: str) -> bool:
        return dev_eui in self._dev_euis
