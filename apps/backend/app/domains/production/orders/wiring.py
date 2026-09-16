from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter

from .commands import (
    CreateProductionOrder,
    DeleteProductionOrder,
    SetProductionOrderArchived,
    UpdateProductionOrder,
)
from .queries import ProductionOrderQueries
from .repository import ProductionOrderRepository


def create_queries(session: AsyncSession) -> ProductionOrderQueries:
    return ProductionOrderQueries(ProductionOrderRepository(session))


def create_order_command(session: AsyncSession) -> CreateProductionOrder:
    return CreateProductionOrder(
        ProductionOrderRepository(session), TransactionalAuditWriter.from_session(session)
    )


def update_order_command(session: AsyncSession) -> UpdateProductionOrder:
    return UpdateProductionOrder(
        ProductionOrderRepository(session), TransactionalAuditWriter.from_session(session)
    )


def set_order_archived_command(session: AsyncSession) -> SetProductionOrderArchived:
    return SetProductionOrderArchived(
        ProductionOrderRepository(session), TransactionalAuditWriter.from_session(session)
    )


def delete_order_command(session: AsyncSession) -> DeleteProductionOrder:
    return DeleteProductionOrder(
        ProductionOrderRepository(session), TransactionalAuditWriter.from_session(session)
    )
