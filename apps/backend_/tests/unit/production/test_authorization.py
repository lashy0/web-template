import pytest

from app.domain.production.permissions import (
    KgPrefixPermission,
    KgVersionPermission,
    ProductionOrderPermission,
)
from tests.unit.route_permissions import assert_routes_require

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_production_order_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListProductionOrders": {ProductionOrderPermission.READ},
            "GetProductionOrder": {ProductionOrderPermission.READ},
            "CreateProductionOrder": {ProductionOrderPermission.CREATE},
            "UpdateProductionOrder": {ProductionOrderPermission.UPDATE},
            "ArchiveProductionOrder": {ProductionOrderPermission.ARCHIVE},
            "RestoreProductionOrder": {ProductionOrderPermission.ARCHIVE},
            "DeleteProductionOrder": {ProductionOrderPermission.DELETE},
        }
    )


def test_kg_prefix_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListKgPrefixes": {KgPrefixPermission.READ},
            "GetKgPrefix": {KgPrefixPermission.READ},
            "CreateKgPrefix": {KgPrefixPermission.CREATE},
            "UpdateKgPrefix": {KgPrefixPermission.UPDATE},
            "ArchiveKgPrefix": {KgPrefixPermission.ARCHIVE},
            "RestoreKgPrefix": {KgPrefixPermission.ARCHIVE},
            "DeleteKgPrefix": {KgPrefixPermission.DELETE},
        }
    )


def test_kg_version_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListKgVersions": {KgVersionPermission.READ},
            "GetKgVersion": {KgVersionPermission.READ},
            "CreateKgVersion": {KgVersionPermission.CREATE},
            "UpdateKgVersion": {KgVersionPermission.UPDATE},
            "ArchiveKgVersion": {KgVersionPermission.ARCHIVE},
            "RestoreKgVersion": {KgVersionPermission.ARCHIVE},
            "DeleteKgVersion": {KgVersionPermission.DELETE},
        }
    )
