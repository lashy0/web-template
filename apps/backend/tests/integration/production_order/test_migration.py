import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.infrastructure.database.fixtures import _database_url

pytestmark = pytest.mark.integration


async def test_migration_preserves_existing_batches_and_can_be_reversed(test_settings):
    schema = f"test_orders_migration_{uuid4().hex}"
    admin = create_async_engine(
        _database_url(
            test_settings, username="postgres_admin", password=os.environ["POSTGRES_ADMIN_PASSWORD"]
        ),
        poolclass=NullPool,
    )
    migrator = create_async_engine(
        _database_url(
            test_settings,
            username="web_app_migrator",
            password=os.environ["POSTGRES_MIGRATOR_PASSWORD"],
        ),
        poolclass=NullPool,
        connect_args={"options": f"-c search_path={schema}"},
    )
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic/versions/2026_09_08_1200_f6a7b8c9d0e2_add_production_orders.py"
    )
    spec = importlib.util.spec_from_file_location("production_orders_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    batch_id = uuid4()

    def check(connection):
        metadata = sa.MetaData()
        batches = sa.Table(
            "batches",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("planned_qty", sa.Integer(), nullable=False),
        )
        metadata.create_all(connection)
        connection.execute(
            batches.insert().values(id=batch_id, name="Existing batch", planned_qty=10)
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            row = connection.execute(
                sa.text("SELECT id, name, planned_qty, production_order_id FROM batches")
            ).one()
            assert tuple(row) == (batch_id, "Existing batch", 10, None)
            foreign_keys = sa.inspect(connection).get_foreign_keys("batches")
            assert foreign_keys[0]["options"]["ondelete"] == "RESTRICT"
            assert "ix_batches_production_order_id" in {
                index["name"] for index in sa.inspect(connection).get_indexes("batches")
            }
            migration.downgrade()
            assert "production_orders" not in sa.inspect(connection).get_table_names()
            assert connection.execute(sa.select(batches)).one().id == batch_id
            migration.upgrade()
            assert connection.scalar(sa.text("SELECT production_order_id FROM batches")) is None

    try:
        async with admin.begin() as connection:
            await connection.execute(
                sa.text(f'CREATE SCHEMA "{schema}" AUTHORIZATION web_app_migrator')
            )
        async with migrator.begin() as connection:
            await connection.run_sync(check)
    finally:
        await migrator.dispose()
        async with admin.begin() as connection:
            await connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()
