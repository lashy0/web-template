import pytest

from app.infrastructure.domain_adapters.verification import SqlAlchemyLatestVerificationProjection


@pytest.mark.unit
def test_latest_verification_projection_is_provided_from_infrastructure() -> None:
    projection = SqlAlchemyLatestVerificationProjection().latest_verification_projection()

    assert set(projection.c.keys()) == {
        "id",
        "kg_dev_eui",
        "status",
        "firmware_version",
        "started_at",
        "rank",
    }
