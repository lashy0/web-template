import pytest

from app.domain.production.schemas import PackingBlocker
from app.domain.production.services._packing import PACKING_ERRORS

pytestmark = pytest.mark.unit


def test_every_packing_blocker_is_the_code_of_its_error() -> None:
    codes = {blocker: error.code for blocker, error in PACKING_ERRORS.items()}

    assert codes == {blocker: blocker.value for blocker in PackingBlocker}
