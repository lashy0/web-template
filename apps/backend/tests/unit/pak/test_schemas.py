import msgspec
import pytest

from app.domain.pak.schemas import PakDeviceCreate, PakDeviceUpdate

pytestmark = pytest.mark.unit


def test_pak_code_accepts_latin_letters_digits_and_separators() -> None:
    data = msgspec.convert({"code": "PAK-01.line_2", "kind": "otk_line"}, PakDeviceCreate)

    assert data.code == "PAK-01.line_2"


@pytest.mark.parametrize(
    "code", ["PAK 01", "-PAK", "ПАК-1", "P" * 129], ids=["space", "leading-dash", "cyrillic", "long"]
)
def test_pak_code_rejects_other_characters_and_long_codes(code: str) -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"code": code}, PakDeviceUpdate)
