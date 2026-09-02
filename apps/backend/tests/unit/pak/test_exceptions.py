import pytest

from app.core.exceptions import AppError
from app.modules.pak.exceptions import (
    InvalidMachineAccessTokenError,
    PakAccessKeyConfigurationError,
    PakAlreadyExistsError,
    PakCannotBeDeletedError,
    PakError,
    PakNotFoundError,
    PakProvisioningError,
    PakTestConfigurationError,
    PakTestNotFoundError,
)


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
        PakTestNotFoundError,
        PakTestConfigurationError,
    ],
)
def test_pak_errors_are_application_errors(error: type[PakError]) -> None:
    assert issubclass(error, PakError)
    assert issubclass(error, AppError)
