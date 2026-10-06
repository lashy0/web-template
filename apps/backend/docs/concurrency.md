# Concurrent edits

Two people may edit the same record at once. Without a check, the one who
saves last silently undoes the other's change. So an update made from a form
names the version it was made from, and the server refuses it when the record
has changed since.

## The version

The version of a record is its `updatedAt`, which Advanced Alchemy moves on
every change of the row. The update routes of the records people edit in forms
require `expectedUpdatedAt` in the body, the `updatedAt` of the copy the change
was made from:

| Route | Body |
|---|---|
| `PATCH /users/{id}`, `PUT /users/{id}/role` | `UserUpdate`, `UserRoleUpdate` |
| `PATCH /paks/{id}` | `PakDeviceUpdate` |
| `PATCH /batches/{id}`, `PUT /batches/{id}/production-order` | `BatchUpdate`, `BatchProductionOrderAssignment` |
| `PATCH /batches/{id}/receipts/{receiptId}`, `PATCH /batches/{id}/shipments/{shipmentId}` | `BatchReceiptUpdate`, `BatchShipmentUpdate` |
| `PATCH /kg/prefixes/{id}`, `PATCH /kg/versions/{id}` | `KgPrefixUpdate`, `KgVersionUpdate` |
| `PATCH /production-orders/{id}` | `ProductionOrderUpdate` |
| `PATCH /defects/groups/{id}`, `PATCH /defects/types/{id}` | `DefectGroupUpdate`, `DefectTypeUpdate` |

When the record's `updatedAt` differs, the answer is 409 with the code
`record_changed`, and nothing is changed. The client reads the record again
and lets the user repeat the change on the new version.

Changes that are not edits of a form, such as archiving or activating, carry
no version: they set one state and are safe to repeat. Completing a shipment
checks the count of its units instead (`expectedQuantity`, see
[shipments](domain/shipments.md)): adding units does not change the
shipment's row, so its `updatedAt` would not tell.

## Implementing it

`app/lib/concurrency.py` holds the pieces:

- an update schema derives from `VersionedUpdate`, which adds the required
  `expected_updated_at`;
- the controller passes `update_changes(data)`, the fields to change without
  the version, and `expected_updated_at=data.expected_updated_at` to the
  service;
- the service reads the record **with a row lock** and calls
  `ensure_unchanged(record, expected_updated_at)` before changing anything,
  so a concurrent update cannot slip in between the check and the write. A
  service method may take `None` to skip the check, for changes made by the
  system.

Every change to a record also announces it (see [realtime](realtime.md)): an
open form learns about a newer version before saving, and the frontend's
`useEditedRecord` keeps the user's input and offers to load the new version.
