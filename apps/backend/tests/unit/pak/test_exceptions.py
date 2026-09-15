import pytest

from app.contexts.equipment.pak.exceptions import (
    InvalidMachineAccessTokenError,
    PakAccessKeyConfigurationError,
    PakAlreadyExistsError,
    PakCannotBeDeletedError,
    PakError,
    PakNotFoundError,
    PakProvisioningError,
)
from app.core.exceptions import AppError


@pytest.mark.unit
@pytest.mark.parametrize(
    "error",
    [
        PakNotFoundError,
        PakAlreadyExistsError,
        PakCannotBeDeletedError,
        PakProvisioningError,
        PakAccessKeyConfigurationError,
        InvalidMachineAccessTokenError,
    ],
)
def test_pak_errors_are_application_errors(error: type[PakError]) -> None:
    assert issubclass(error, PakError)
    assert issubclass(error, AppError)
