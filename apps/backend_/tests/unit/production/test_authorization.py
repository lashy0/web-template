import pytest

from app.domain.production.permissions import ProductionOrderPermission
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
