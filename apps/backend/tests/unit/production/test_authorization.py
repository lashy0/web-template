import pytest

from app.db.enums import UserRole
from app.domain.production.permissions import (
    BatchPermission,
    KgPrefixPermission,
    KgUnitPermission,
    KgVersionPermission,
    MulticastGroupPermission,
    PackingPermission,
    ProductionOrderPermission,
)
from app.server.authorization import create_authorization_policy
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


def test_multicast_group_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListMulticastGroups": {MulticastGroupPermission.READ},
            "GetMulticastGroup": {MulticastGroupPermission.READ},
            "GetMulticastGroupKeys": {MulticastGroupPermission.READ_KEYS},
            "CreateMulticastGroup": {MulticastGroupPermission.CREATE},
            "UpdateMulticastGroup": {MulticastGroupPermission.UPDATE},
            "ArchiveMulticastGroup": {MulticastGroupPermission.ARCHIVE},
            "RestoreMulticastGroup": {MulticastGroupPermission.ARCHIVE},
            "DeleteMulticastGroup": {MulticastGroupPermission.DELETE},
        }
    )


def test_batch_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListBatches": {BatchPermission.READ},
            "GetBatch": {BatchPermission.READ},
            "PreviewBatchDevEuiRange": {BatchPermission.CREATE},
            "CreateBatch": {BatchPermission.CREATE},
            "UpdateBatch": {BatchPermission.UPDATE},
            "AssignBatchProductionOrder": {BatchPermission.ASSIGN_PRODUCTION_ORDER},
            "CompleteBatch": {BatchPermission.COMPLETE},
            "ArchiveBatch": {BatchPermission.ARCHIVE},
            "RestoreBatch": {BatchPermission.ARCHIVE},
            "DeleteBatch": {BatchPermission.DELETE},
        }
    )


def test_batch_receipt_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListBatchReceipts": {BatchPermission.READ},
            "GetBatchReceipt": {BatchPermission.READ},
            "CreateBatchReceipt": {BatchPermission.CREATE_RECEIPT},
            "UpdateBatchReceipt": {BatchPermission.UPDATE_RECEIPT},
            "VoidBatchReceipt": {BatchPermission.VOID_RECEIPT},
        }
    )


def test_packing_routes_require_packing_pack() -> None:
    assert_routes_require(
        {
            "FindPackingUnit": {PackingPermission.PACK},
            "PackKgUnit": {PackingPermission.PACK},
        }
    )


@pytest.mark.parametrize(
    ("role", "granted"),
    [
        (UserRole.ADMINISTRATOR, True),
        (UserRole.MANAGER, False),
        (UserRole.ENGINEER, False),
        (UserRole.PACKER, True),
        (UserRole.OPERATOR, False),
    ],
)
def test_roles_get_packing_pack(role: UserRole, granted: bool) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert (PackingPermission.PACK in permissions) is granted


def test_kg_unit_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListKgUnits": {KgUnitPermission.READ},
            "GetKgUnit": {KgUnitPermission.READ},
            "GetKgUnitCredentials": {KgUnitPermission.READ_CREDENTIALS},
        }
    )


def test_batch_shipment_routes_use_operation_specific_permissions() -> None:
    assert_routes_require(
        {
            "ListBatchShipments": {BatchPermission.READ},
            "GetBatchShipment": {BatchPermission.READ},
            "CreateBatchShipment": {BatchPermission.CREATE_SHIPMENT},
            "UpdateBatchShipment": {BatchPermission.UPDATE_SHIPMENT},
            "CompleteBatchShipment": {BatchPermission.COMPLETE_SHIPMENT},
            "VoidBatchShipment": {BatchPermission.VOID_SHIPMENT},
            "ListBatchShipmentItems": {BatchPermission.READ},
            "AddBatchShipmentUnits": {BatchPermission.UPDATE_SHIPMENT},
            "AddPackedBatchShipmentUnits": {BatchPermission.UPDATE_SHIPMENT},
            "RemoveBatchShipmentUnit": {BatchPermission.UPDATE_SHIPMENT},
        }
    )


@pytest.mark.parametrize(
    ("role", "granted"),
    [
        (UserRole.ADMINISTRATOR, True),
        (UserRole.MANAGER, False),
        (UserRole.ENGINEER, False),
    ],
)
def test_only_administrators_read_kg_unit_credentials(role: UserRole, granted: bool) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert (KgUnitPermission.READ_CREDENTIALS in permissions) is granted


@pytest.mark.parametrize(
    ("role", "granted"),
    [
        (UserRole.ADMINISTRATOR, True),
        (UserRole.MANAGER, False),
        (UserRole.ENGINEER, False),
    ],
)
def test_only_administrators_read_multicast_group_keys(role: UserRole, granted: bool) -> None:
    permissions = create_authorization_policy().permissions_for_role(role)

    assert (MulticastGroupPermission.READ_KEYS in permissions) is granted
