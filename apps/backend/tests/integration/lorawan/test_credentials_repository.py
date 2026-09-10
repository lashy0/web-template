import base64
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import Batch, BatchLoRaWanConfig, BatchStatus
from app.modules.kg.exceptions import KgLoRaWanCredentialsAlreadyExistError
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit, LoRaWanCredentials
from app.modules.kg.services.credentials import LoRaWanCredentialsService
from app.modules.lorawan import (
    ActivationType,
    LoRaWanVersion,
    generate_credentials,
)


async def _kg_with_lorawan_config(session: AsyncSession) -> KgUnit:
    prefix = KgDevEuiPrefix(prefix=uuid4().hex[:10], short_code=uuid4().hex[:8])
    batch = Batch(
        id=uuid4(),
        name="Credentials batch",
        description=None,
        planned_qty=1,
        day_plan_qty=1,
        status=BatchStatus.IN_PRODUCTION,
        dev_eui_prefix=prefix.prefix,
        created_by_user_id=None,
        lorawan_config=BatchLoRaWanConfig(
            activation_type=ActivationType.ABP,
            lorawan_version=LoRaWanVersion.V1_1,
            join_eui=uuid4().hex[:16],
        ),
    )
    kg = KgUnit(
        dev_eui="0123456789abcdef",
        short_id="kg-89abcdef",
        batch=batch,
        status=KgStatus.REGISTERED,
    )
    session.add_all([prefix, batch, kg])
    await session.flush()
    return kg


def _encryption_key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(bytes(range(32))).decode("ascii"))


@pytest.mark.integration
async def test_credentials_are_encrypted_in_db_and_cannot_be_saved_twice(
    db_session: AsyncSession,
) -> None:
    kg = await _kg_with_lorawan_config(db_session)
    credentials = generate_credentials(
        kg.dev_eui,
        ActivationType.ABP,
        LoRaWanVersion.V1_1,
    )
    service = LoRaWanCredentialsService(db_session, _encryption_key())

    assert not await service.credentials_exist(kg_dev_eui=kg.dev_eui)
    await service.save_credentials(kg_dev_eui=kg.dev_eui, credentials=credentials)
    assert await service.credentials_exist(kg_dev_eui=kg.dev_eui)

    stored = await db_session.scalar(
        select(LoRaWanCredentials).where(LoRaWanCredentials.kg_dev_eui == kg.dev_eui)
    )
    assert stored is not None
    assert stored.encrypted_data != credentials.model_dump_json().encode("utf-8")
    for value in credentials.model_dump().values():
        assert value.encode("utf-8") not in stored.encrypted_data
    assert await service.load_credentials(kg_dev_eui=kg.dev_eui) == credentials

    with pytest.raises(KgLoRaWanCredentialsAlreadyExistError):
        await service.save_credentials(kg_dev_eui=kg.dev_eui, credentials=credentials)

    # Even bypassing the service cannot overwrite the one-to-one credential row.
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                insert(LoRaWanCredentials).values(
                    kg_dev_eui=kg.dev_eui,
                    schema_version=1,
                    encrypted_data=b"replacement",
                )
            )
